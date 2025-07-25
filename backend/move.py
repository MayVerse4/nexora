import os
import json
import io
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Define Gmail API Scopes (ensure label creation & email modification)
SCOPES = ["https://www.googleapis.com/auth/gmail.modify", 
          "https://www.googleapis.com/auth/gmail.labels"]

def authenticate_gmail():
    """Authenticate user and return Gmail service instance."""
    creds = None

    # Load credentials
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # Refresh or request new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        # Save new credentials
        with open("token.json", "w") as token_file:
            token_file.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)

def get_existing_labels(service):
    """Fetch all existing labels in Gmail."""
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    return {label["name"].lower(): label["id"] for label in labels}

def create_label(service, label_name):
    """Create a new label in Gmail and return its ID."""
    label_body = {"name": label_name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
    new_label = service.users().labels().create(userId="me", body=label_body).execute()
    print(f"✅ Created label: {label_name}")
    return new_label["id"]

def move_email_to_label(service, email_id, label_id):
    """Move an email to the specified label in Gmail."""
    try:
        service.users().messages().modify(
            userId="me",
            id=email_id,
            body={"addLabelIds": [label_id], "removeLabelIds": ["INBOX"]}
        ).execute()
        print(f"✅ Moved Email ID {email_id} to label {label_id}")
    except Exception as e:
        print(f" Error moving email {email_id}: {e}")

def process_emails():
    """Read categorized emails and move them to respective labels."""
    service = authenticate_gmail()

    # Load categorized email data
    with open("categorized_emails.json", "r") as file:
        emails = json.load(file)

        
    # Step 1: Identify which categories exist in the emails
    required_categories = set(email.get("category", "").strip().lower() for email in emails)

    # Step 2: Predefine valid labels (to avoid extra labels)
    valid_labels = {"work", "personal", "orders", "banking", "spam"}


    # Step 3: Ensure only labels that exist in categorized emails are created
    needed_labels = required_categories.intersection(valid_labels)

    # Step 4: Get existing labels from Gmail
    existing_labels = get_existing_labels(service)

    # Step 5: Create only necessary labels
    label_mapping = {}
    for label in needed_labels:
        if label in existing_labels:
            label_mapping[label] = existing_labels[label]
        else:
            label_mapping[label] = create_label(service, label.capitalize())  # Ensure correct capitalization

    # Step 6: Move emails to correct labels
    for email in emails:
        category = email.get("category", "").strip().lower()
        email_id = email["id"]
        
        if category in label_mapping:
            move_email_to_label(service, email_id, label_mapping[category])
        else:
            print(f"⚠️ Skipping Email ID {email_id}, no matching label found for category: {category}")

if __name__ == "__main__":
    process_emails()

