import os
import time
from datetime import datetime, timezone, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError  # ✅ Fixed Import

# ✅ SCOPES to allow both moving emails to trash & permanent deletion
SCOPES = ["https://mail.google.com/"]

def authenticate_gmail():
    """Authenticate user and return Gmail service instance."""
    creds = None
    try:
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    except:
        pass

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)

def get_old_emails(days, max_attempts=3):
    """Fetch emails older than a given number of days with retry mechanism."""
    service = authenticate_gmail()
    date_threshold = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y/%m/%d')
    query = f"before:{date_threshold}"

    attempt = 0
    while attempt < max_attempts:
        try:
            results = service.users().messages().list(userId="me", q=query, maxResults=20).execute()
            messages = results.get("messages", [])

            email_list = []
            sender_dict = {}

            for msg in messages:
                try:
                    msg_data = service.users().messages().get(
                        userId="me", id=msg["id"], format="metadata"
                    ).execute()

                    headers = msg_data.get("payload", {}).get("headers", [])
                    sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")
                    subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
                    date_received = next((h["value"] for h in headers if h["name"] == "Date"), "Unknown Date")

                    email_list.append({"id": msg["id"], "sender": sender, "subject": subject, "date": date_received})

                    if sender in sender_dict:
                        sender_dict[sender].append(msg["id"])
                    else:
                        sender_dict[sender] = [msg["id"]]
                
                except HttpError as e:  # ✅ Fixed Error Handling
                    print(f"❌ Error fetching email: {e}")
                    continue

            return email_list, sender_dict
        
        except TimeoutError:
            attempt += 1
            print(f"⚠️ Timeout Error! Retrying {attempt}/{max_attempts}...")
            time.sleep(2)
    
    print("❌ Failed to fetch emails after multiple attempts.")
    return [], {}

def delete_emails(selected_ids, delete_type="trash"):
    """Move selected emails to trash or permanently delete them."""
    service = authenticate_gmail()

    for email_id in selected_ids:
        try:
            if delete_type == "trash":
                service.users().messages().modify(
                    userId="me", id=email_id, body={"removeLabelIds": [], "addLabelIds": ["TRASH"]}
                ).execute()
                print(f"✅ Moved to Trash: {email_id}")
            elif delete_type == "delete":
                service.users().messages().delete(userId="me", id=email_id).execute()
                print(f"🚨 Permanently Deleted: {email_id}")
        except HttpError as e:
            print(f"❌ Failed to delete email {email_id}: {e}")

if __name__ == "__main__":
    time_options = {
        "1": 365,  # 1 Year
        "2": 180,  # 6 Months
        "3": 90,   # 3 Months
        "4": 30    # 30 Days
    }

    print("🔹 Choose emails older than:\n1️⃣ 1 Year  2️⃣ 6 Months  3️⃣ 3 Months  4️⃣ 30 Days")
    time_choice = input("Enter your choice (1, 2, 3, 4): ")

    if time_choice not in time_options:
        print("❌ Invalid choice! Exiting...")
        exit()

    days_old = time_options[time_choice]
    emails, senders = get_old_emails(days_old)

    if not emails:
        print("\n🚫 No emails found for the selected time range. Exiting...")
        exit()

    print(f"\n🔍 Searching for emails before: {days_old} days ago\n")
    print("🔹 **Available Emails:**")
    for i, email in enumerate(emails, 1):
        print(f"{i}️⃣ **Sender:** {email['sender']} | **Subject:** {email['subject']} | 📅 **Date:** {email['date']}")

    print("\n🔹 **Available Senders for Bulk Deletion:**")
    for i, sender in enumerate(senders.keys(), 1):
        print(f"{i}️⃣ {sender}")

    choice = input("\n🔹 Delete by: 1️⃣ Email Number  2️⃣ Sender Email Address\nEnter choice (1 or 2): ")

    selected_ids = []
    
    if choice == "1":
        email_numbers = input("Enter email numbers to delete (comma-separated), or type 'all' to delete everything: ")
        if email_numbers.lower() == "all":
            selected_ids = [email["id"] for email in emails]
        else:
            try:
                selected_ids = [emails[int(num) - 1]["id"] for num in email_numbers.split(",") if num.isdigit()]
            except (IndexError, ValueError):
                print("❌ Invalid email selection! Exiting...")
                exit()

    elif choice == "2":
        sender_choice = input("Enter the number of the sender whose emails you want to delete: ")
        if sender_choice.isdigit() and 1 <= int(sender_choice) <= len(senders):
            sender_email = list(senders.keys())[int(sender_choice) - 1]
            selected_ids = senders[sender_email]
        else:
            print("❌ Invalid sender selection! Exiting...")
            exit()
    else:
        print("❌ Invalid choice! Exiting...")
        exit()

    delete_type = input("\n🗑️ Choose Deletion Type:\n1️⃣ Move to Trash (Recoverable)\n2️⃣ Permanently Delete\nEnter your choice (1 or 2): ")
    if delete_type == "2":
        confirm = input("⚠️ Are you sure you want to permanently delete these emails? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("🚫 Deletion cancelled. Exiting...")
            exit()

    delete_mode = "trash" if delete_type == "1" else "delete"
    delete_emails(selected_ids, delete_mode)
