import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Define the required Gmail API scopes
SCOPES = ["https://www.googleapis.com/auth/gmail.modify", 
          "https://www.googleapis.com/auth/gmail.labels"]

def authenticate_gmail():
    """Authenticate user and return Gmail service instance."""
    creds = None

    # Load previously saved credentials
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # If credentials are invalid, refresh or request new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the new credentials for future use
        with open("token.json", "w") as token_file:
            token_file.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)

def fetch_emails():
    """Fetch latest 10 emails with headers only."""
    service = authenticate_gmail()

    # Query to fetch emails only from INBOX and exclude CATEGORY_PROMOTIONS
    query = "in:inbox -category:promotions"

    results = service.users().messages().list(userId="me", maxResults=4, q=query).execute()
    messages = results.get("messages", [])

    email_metadata = []

    for msg in messages:
        msg_id = msg["id"]
        msg_details = service.users().messages().get(userId="me", id=msg_id, format="metadata").execute()
        
        headers = msg_details.get("payload", {}).get("headers", [])

        # Extract useful metadata
        email_info = {
            "id": msg_id,
            "subject": next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject"),
            "from": next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender"),
            "date": next((h["value"] for h in headers if h["name"] == "Date"), "Unknown Date")
        }

        email_metadata.append(email_info)

    # Save metadata to a JSON file
    with open("email_metadata.json", "w") as json_file:
        json.dump(email_metadata, json_file, indent=4)

    print("✅ Email metadata saved to email_metadata.json")

if __name__ == "__main__":
    fetch_emails()
