import json
import requests
import re
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def authenticate_gmail():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token_file:
            token_file.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def extract_unsubscribe_link(header_value):
    if not header_value:
        return None
    urls = re.findall(r"https?://[^\s,<>]+", header_value)
    return urls[0] if urls else None

def label_unsubscribed_email(service, email_id):
    try:
        service.users().labels().create(
            userId="me",
            body={"name": "Nexora-Unsubscribed", "labelListVisibility": "labelShow"}
        ).execute()
    except:
        pass  # Label already exists

    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    label_id = next((label["id"] for label in labels if label["name"] == "Nexora-Unsubscribed"), None)

    if label_id:
        service.users().messages().modify(
            userId="me",
            id=email_id,
            body={"addLabelIds": [label_id]}
        ).execute()

def is_already_labeled_unsubscribed(service, email_id):
    try:
        msg = service.users().messages().get(userId="me", id=email_id, format="metadata").execute()
        label_ids = msg.get("labelIds", [])
        labels = service.users().labels().list(userId="me").execute().get("labels", [])
        for label in labels:
            if label["name"] == "Nexora-Unsubscribed" and label["id"] in label_ids:
                return True
        return False
    except:
        return False

def get_unique_mailing_list_senders():
    service = authenticate_gmail()
    if not service:
        return {}

    try:
        results = service.users().messages().list(userId="me", maxResults=30).execute()
        messages = results.get("messages", [])
    except Exception as e:
        return {"error": f"❌ Failed to retrieve messages: {e}"}

    unique_senders = {}
    for msg in messages:
        email_id = msg["id"]

        if is_already_labeled_unsubscribed(service, email_id):
            continue

        try:
            msg_data = service.users().messages().get(userId="me", id=email_id, format="metadata").execute()
        except Exception as e:
            print(f"⚠️ Could not read email ID {email_id}: {e}")
            continue

        headers = msg_data.get("payload", {}).get("headers", [])
        sender_email, unsubscribe_link = None, None
        for header in headers:
            if header["name"].lower() == "from":
                sender_email = header["value"]
            if header["name"].lower() == "list-unsubscribe":
                unsubscribe_link = header["value"]

        if sender_email and sender_email not in unique_senders:
            unique_senders[sender_email] = {
                "email_id": email_id,
                "unsubscribe": unsubscribe_link
            }

    return unique_senders

def unsubscribe_from_mailing_list(email_id, unsubscribe_link, sender_email):
    service = authenticate_gmail()
    if not service:
        return f"❌ Gmail authentication failed for {sender_email}.\n"

    unsubscribe_url = extract_unsubscribe_link(unsubscribe_link)
    if unsubscribe_url:
        try:
            response = requests.get(unsubscribe_url, timeout=5)
            if response.status_code == 200:
                label_unsubscribed_email(service, email_id)
                return f"✅ Successfully unsubscribed from {sender_email}\n"
            else:
                selenium_result = unsubscribe_with_selenium(unsubscribe_url)
                label_unsubscribed_email(service, email_id)
                return f"⚠️ Direct request failed. Tried Selenium for {sender_email}: {selenium_result}\n"
        except Exception as e:
            selenium_result = unsubscribe_with_selenium(unsubscribe_url)
            label_unsubscribed_email(service, email_id)
            return f"⚠️ Request error for {sender_email}: {e}\n{selenium_result}\n"
    else:
        return f"❌ No valid unsubscribe URL found for {sender_email}\n"

def unsubscribe_with_selenium(unsubscribe_url):
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        driver = webdriver.Chrome(options=options)
        driver.get(unsubscribe_url)

        try:
            button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH,
                    "//a[contains(translate(text(),'UNSUBSCRIBE','unsubscribe'),'unsubscribe')] | " +
                    "//button[contains(translate(text(),'UNSUBSCRIBE','unsubscribe'),'unsubscribe')]"
                ))
            )
            button.click()
            # Removed: time.sleep(5)
            driver.quit()
            return "✅ Unsubscribed using Selenium."
        except:
            current_url = driver.current_url
            driver.quit()
            return f"⚠️ No unsubscribe button found on page. Try manually: {current_url}"
    except Exception as e:
        return f"⚠️ Selenium Error: {e}"

def main(selected_indices=None):
    output = ""
    senders = get_unique_mailing_list_senders()
    if not senders:
        return "❌ No mailing list emails found.\n"

    output += "\n🔹 Subscriptions Found:\n"
    sender_list = list(senders.keys())

    if selected_indices is None:
        for i, sender_email in enumerate(sender_list):
            output += f"{i+1}. {sender_email}\n"
        return output

    for index in selected_indices:
        if 0 <= index < len(sender_list):
            sender_email = sender_list[index]
            email_id = senders[sender_email]["email_id"]
            unsubscribe_link = senders[sender_email]["unsubscribe"]
            result = unsubscribe_from_mailing_list(email_id, unsubscribe_link, sender_email)
            output += f"{index+1}. {sender_email}\n{result}\n"

            with open("unsubscribed_log.txt", "a") as log_file:
                log_file.write(f"{sender_email} | {unsubscribe_link}\n")
        else:
            output += f"❌ Invalid selection: {index+1}\n"
    return output

if __name__ == "__main__":
    print(main())
