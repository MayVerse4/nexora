<!-- Rectangle image banner -->
<p align="center">
  <img src="static/banner.png" alt="Nexora Banner" width="100%">
</p>

# 📧 Nexora: AI-Powered Email Assistant

**Nexora** is a productivity-focused AI email assistant that automates inbox management tasks such as categorizing, cleaning up unwanted emails, deleting drafts, and bulk unsubscribing — all through a simple and intuitive interface.

---

## 🚀 Core Functionalities

1. **🔐 Gmail Login**
   - Google OAuth2 login for secure access to your Gmail inbox.

2. **📂 Email Categorization**
   - Automatically categorizes your emails using AI.
   - Sorts messages into labels like Promotions, Personal, or Spam.

3. **🗑️ Email Deletion**
   - AI suggests unwanted emails for deletion.
   - Supports both soft delete (Gmail Bin) and permanent delete options.

4. **📝 Draft Cleanup**
   - Detects unused or old email drafts and removes them in bulk.

5. **📬 Bulk Unsubscribe**
   - Identifies newsletters and promotional senders.
   - Lets you unsubscribe and delete all emails from selected sources.

6. **💥 Self-Destruction**
   - A placeholder for wiping inbox data or deleting multiple categories of emails with a single click.

---

## 🖼️ UI Pages

- `index.html` → Welcome page with **Get Started** button  
- `login.html` → Google login screen  
- `main.html` → Dashboard for choosing features  
- `categorize.html` → Displays categorized email results  
- `delete.html` → Shows AI-suggested deletions  
- `drafts.html` → Displays old drafts for cleanup  
- `unsubscribe.html` → Bulk unsubscribe interface  

---

## 🛠️ Tech Stack

- **Backend**: Python 3, Flask
- **Frontend**: HTML5, CSS3
- **AI & Logic**: Gemma-Openrouter
- **APIs**: Gmail API, OAuth 2.0

---

## 🔒 Privacy & Security

- Nexora **does not access or store full email content**.
- Only uses **email metadata** such as subject, sender, and timestamp.
- All interactions happen locally and securely through Gmail’s official API.

---

## 📁 Project Structure

```
nexora/
│
├── static/
│   └── your-banner.png         # Top banner image for README/UI
│   └── styles.css              # Shared styles
│
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── main.html
│   ├── categorize.html
│   ├── delete.html
│   ├── drafts.html
│   ├── unsubscribe.html
│
├── fetch.py                    # Gmail API + OAuth handling
├── categorize.py               # AI model to classify emails
├── delete.py                   # Email deletion + draft cleanup
├── unsubscribe.py              # Bulk unsubscribe logic
├── server.py                   # Flask routes & logic
└── requirements.txt            # Python package dependencies
```

---

## 🧪 How to Run Locally

Follow these steps to run Nexora on your local machine:

```bash
git clone https://github.com/MayVerse4/nexora.git
cd nexora
pip install -r requirements.txt
python server.py
```

Once the server is running, open your browser and go to:  
👉 **http://127.0.0.1:5000/**

---

## ✍️ Contributors

- **[Your Name]** – Project Lead & Developer  
- *(Optional: Add names of teammates or collaborators here)*
