import json
import requests

# Load OpenRouter API Key
API_KEY = "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"  # 🔴 Replace with your actual API key

# Load email metadata from previous phase
with open("email_metadata.json", "r") as file:
    emails = json.load(file)

# Define the AI API endpoint
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Function to send email data to AI and categorize
def categorize_email(email):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # Construct AI prompt
    prompt = f"""

    

    You are an intelligent email organizer that categorizes emails into one of the following categories:

1️⃣ Work
Emails related to job, office, professional tasks, colleagues, projects, job offers, HR communications, or official company emails.
Includes meeting invites, client interactions, project updates, internal company announcements.
2️⃣ Personal
Emails from friends, family, or personal contacts.
Includes invitations (weddings, birthdays, events), travel plans, greetings, and casual discussions.
3️⃣ Orders
Emails containing purchase confirmations, order receipts, shipping updates, delivery notifications, invoices.
Typically from e-commerce platforms (Amazon, Flipkart, Myntra, Swiggy, Zomato, etc.) or service providers (Uber, Ola, Jio, Airtel, etc.).
4️⃣ Banking
Emails related to bank statements, transaction alerts, credit card bills, loan updates, investment reports, and tax documents.
Usually sent by banks, financial institutions, payment gateways (PayPal, Razorpay, Stripe, etc.).
5️⃣ Spam
Suspicious, unknown senders, scam emails, phishing attempts, repetitive marketing emails, lottery or prize-winning claims.
If the email urges urgent action, offers unrealistic prizes, or has excessive use of words like “Congratulations”, “Claim now”, “Limited-time offer”, classify it as Spam.
🔹 Categorization Rules
✔ Personal Emails:

If both Subject and Sender indicate personal intent (e.g., "Hey, how are you?" from a known person), classify as Personal.
Emails containing greetings, casual discussions, or invitations from known senders.
✔ Work Emails:

If the Sender domain is corporate (e.g., @company.com, @organization.org) OR
The Subject contains keywords like job, HR, project, official, work update, meeting, client, classify as Work.
✔ Order Emails:

If the Subject contains phrases like "Order Confirmation", "Your Package is on the way", "Shipping Update", "Invoice attached" OR
The Sender is an e-commerce or service provider domain (e.g., @amazon.com, @flipkart.com, @swiggy.in), classify as Orders.

✔ Banking Emails:

If the Sender is a media company or newsletter platform (e.g., @nytimes.com, @medium.com, @substack.com) OR
The Subject contains phrases like "Your Daily Digest", "Newsletter Update", "New Blog Post", classify as News & Subscriptions.
✔ Spam Emails:

If the Sender is unknown, AND
The Subject contains suspicious phrases like "Win a free iPhone", "Urgent action required", "Claim your prize", classify as Spam.
If the email asks for personal details, banking info, or login credentials, it is likely phishing and should be Spam.
🔹 Email Data for Categorization
    Subject: {email['subject']}
    Sender: {email['from']}
    Date: {email['date']}
    👉 Analyze the subject and sender and respond ONLY with the exact category (no explanation), in one word from: Work, Personal, Orders, Banking, Spam, News, or Uncategorized."
    """

    # Prepare request payload
    data = {
        "model": "openai/gpt-3.5-turbo",  # Change model if needed (e.g., gpt-3.5) (deepseek/deepseek-r1-0528-qwen3-8b:free)
        "messages": [
            {"role": "system", "content": "You are an email organizer."},
            {"role": "user", "content": prompt}
        ]
    }

    # Send request to OpenRouter AI
    response = requests.post(API_URL, headers=headers, json=data)

    if response.status_code == 200:
        ai_response = response.json()
        if "choices" in ai_response and ai_response["choices"]:
            return ai_response["choices"][0]["message"]["content"].strip()
        else:
            print("❌ AI response did not contain 'choices'.")
            return "Uncategorized"
    else:
        print(f"❌ Error: {response.text}")
        return "Uncategorized"

# Process all emails
for email in emails:
    email["category"] = categorize_email(email)

# Save categorized emails to a new file
with open("categorized_emails.json", "w") as file:
    json.dump(emails, file, indent=4)

print("✅ Categorized emails saved to categorized_emails.json")
