from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import time
import os
import re
from google.oauth2.credentials import Credentials


# Global tracking store
tracked_emails = []  # Track both email ID and keyword pairs

# Define the required Gmail API scopes
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def authenticate_gmail():
    """Authenticate user and return Gmail service instance."""
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)

def get_emails(service):
    """Fetch recent emails and display choices for self-destruction."""
    results = service.users().messages().list(userId="me", maxResults=10).execute()
    messages = results.get("messages", [])

    if not messages:
        print("📭 No emails found.")
        return []

    print("\n📩 **Select Emails for Self-Destruction**")
    email_list = []
    
    for idx, message in enumerate(messages[:10], start=1):
        msg = service.users().messages().get(userId="me", id=message["id"]).execute()
        headers = msg["payload"]["headers"]
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")

        print(f"{idx}️⃣ {subject} (From: {sender})")
        email_list.append((message["id"], subject, sender))

    return email_list

def check_if_read(service, email_id):
    """Check if an email has been read (moved out of 'Unread')."""
    msg = service.users().messages().get(userId="me", id=email_id, format="metadata").execute()
    labels = msg.get("labelIds", [])
    return "UNREAD" not in labels  # If UNREAD is not in labels, it means email is read

def delete_email(service, email_id, delete_mode, email_info):
    """Delete an email based on the selected mode."""
    if delete_mode == "trash":
        service.users().messages().trash(userId="me", id=email_id).execute()
    else:
        service.users().messages().delete(userId="me", id=email_id).execute()
    
    print(f"✅ **Email '{email_info[1]}' from {email_info[2]} has been deleted.**")

def track_and_delete_future_emails(service, delete_keywords, delete_mode, time_limit):
    print("\n🔄 **Currently tracking the following email+keyword pairs:**")
    for e, k in tracked_emails:
        print(f"   📧 {e} — Keyword: '{k}'")

    while True:
        results = service.users().messages().list(userId="me", maxResults=10).execute()
        messages = results.get("messages", [])

        for message in messages:
            msg = service.users().messages().get(userId="me", id=message["id"]).execute()
            headers = msg["payload"]["headers"]
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "")

            match = re.search(r"<(.+?)>", sender)
            clean_sender = match.group(1).lower() if match else sender.lower()

            for tracked_email, tracked_keyword in tracked_emails:
                email_match = tracked_email.lower() == clean_sender
                keyword_match = tracked_keyword.lower() in subject.lower()

                if email_match and keyword_match:
                    email_info = (message["id"], subject, clean_sender)

                    print(f"🚨 New email detected: '{subject}' from {clean_sender}! Scheduled for deletion.")

                    if time_limit == "open":
                        print(f"👀 Waiting for email '{subject}' to be opened...")
                        while not check_if_read(service, message["id"]):
                            time.sleep(5)
                        print(f"📬 Email '{subject}' has been opened. Deleting now...")
                    else:
                        print(f"⏳ Email '{subject}' will be deleted in {time_limit // 60} minutes...")
                        time.sleep(time_limit)

                    delete_email(service, message["id"], delete_mode, email_info)
                    break  # Exit after handling one valid match
                else:
                    # Optional debug log (you can comment this out)
                    print(f"🔎 Skipped: sender='{clean_sender}' subject='{subject}' didn’t match tracked email='{tracked_email}' + keyword='{tracked_keyword}'")

                    time.sleep(10)

def self_destruct_emails(service, email_list):
    """User selects emails for self-destruction."""
    selected = input("\nEnter the number(s) of emails to self-destruct (comma-separated): ")
    selected_ids = [email_list[int(num)-1] for num in selected.split(",") if num.isdigit()]

    # Fix: Ensure delete_keywords is always defined
    delete_keywords = input("\n🔍 Enter keywords to delete emails (e.g., OTP, Verification Code): ").strip()
    if not delete_keywords:
        print("❌ No keywords provided. Skipping deletion.")
        return
    
    delete_keywords = delete_keywords.split(",")

    # Add selected emails and their corresponding keywords to tracked_emails list
    for email_id, subject, sender in selected_ids:
        match = re.search(r"<(.+?)>", sender)
        clean_sender = match.group(1).lower() if match else sender.lower()
        for keyword in delete_keywords:
            if any(kw.lower() in subject.lower() for kw in [keyword]):
                tracked_emails.append((clean_sender, keyword.lower()))

    print("\n⏳ **Set Self-Destruction Timer**")
    print("1️⃣ Delete After Opening")
    print("2️⃣ Delete After 10 minutes")
    print("3️⃣ Delete After 1 hour")
    print("4️⃣ Delete After 1 day")
    time_choice = input("Enter your choice (1-4): ")

    time_map = {"1": "open", "2": 600, "3": 3600, "4": 86400}  # Time in seconds
    delete_time = time_map.get(time_choice, "open")

    print("\n🔥 **Self-Destruct Mode: Confirm Deletion Type**")
    print("1️⃣ Move to Trash (Recoverable)")
    print("2️⃣ Permanently Delete")
    delete_choice = input("Enter your choice (1 or 2): ")
    delete_mode = "trash" if delete_choice == "1" else "delete"

    print("\n🚀 **Self-Destruction Activated!** Emails will be deleted based on your selection.")

    # Start tracking future emails matching the same keywords
    track_and_delete_future_emails(service, delete_keywords, delete_mode, delete_time)

def main():
    print("🔒 **Welcome to Nexora's Self-Destruct Emails** 🔥")
    service = authenticate_gmail()
    
    email_list = get_emails(service)
    if email_list:
        self_destruct_emails(service, email_list)

if __name__ == "__main__":
    main()
