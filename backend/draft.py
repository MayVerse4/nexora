import os
import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

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

def fetch_all_drafts():
    service = authenticate_gmail()
    result = service.users().drafts().list(userId="me", maxResults=500).execute()
    return result.get("drafts", [])

def get_subject(headers, snippet):
    subject = next((h["value"] for h in headers if h["name"] == "Subject"), None)
    if subject:
        return subject
    return f"📌 (No Subject - {snippet[:30]}...)" if snippet else "📌 (Empty Draft)"

def analyze_drafts():
    service = authenticate_gmail()
    drafts = fetch_all_drafts()

     # Initialize categories
    categorized = {
        "Today": [],
        "1-day old": [],
        "7-days old": [],
        "30-days old": [],
        "3-months old": [],
        "6-months old": [],
        "1-year old": [],
        "1+ year old": []
    }

    all_drafts = []

    for draft in drafts:
        draft_id = draft["id"]
        draft_data = service.users().drafts().get(userId="me", id=draft_id).execute()
        message = draft_data.get("message", {})
        headers = message.get("payload", {}).get("headers", [])
        snippet = message.get("snippet", "")

        subject = get_subject(headers, snippet)
        date_str = next((h["value"] for h in headers if h["name"] == "Date"), None)

        days_old = None
        if date_str:
            try:
                draft_date = datetime.datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                days_old = (now_utc - draft_date).days
            except Exception as e:
                days_old = None

        # Categorize based on days_old
        if days_old is None:
            continue
        elif days_old == 0:
            categorized["Today"].append((subject, draft_id))
        elif days_old == 1:
            categorized["1-day old"].append((subject, draft_id))
        elif 2 <= days_old <= 7:
            categorized["7-days old"].append((subject, draft_id))
        elif 8 <= days_old <= 30:
            categorized["30-days old"].append((subject, draft_id))
        elif 31 <= days_old <= 90:
            categorized["3-months old"].append((subject, draft_id))
        elif 91 <= days_old <= 180:
            categorized["6-months old"].append((subject, draft_id))
        elif 181 <= days_old <= 365:
            categorized["1-year old"].append((subject, draft_id))
        elif days_old > 365:
            categorized["1+ year old"].append((subject, draft_id))

        all_drafts.append((subject, draft_id))

    return categorized, all_drafts

def delete_draft_by_id(draft_id):
    service = authenticate_gmail()
    service.users().drafts().delete(userId="me", id=draft_id).execute()
    return 1

def delete_drafts_by_category(category):
    service = authenticate_gmail()
    categorized, _ = analyze_drafts()
    deleted = []
    if category in categorized:
        for _, draft_id in categorized[category]:
            service.users().drafts().delete(userId="me", id=draft_id).execute()
            deleted.append(draft_id)
    return len(deleted)

def delete_all_drafts():
    service = authenticate_gmail()
    _, all_drafts = analyze_drafts()
    deleted = []
    for _, draft_id in all_drafts:
        service.users().drafts().delete(userId="me", id=draft_id).execute()
        deleted.append(draft_id)
    return len(deleted)

