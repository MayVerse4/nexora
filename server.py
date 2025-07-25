from flask import Flask, render_template,Response, redirect, url_for, request, jsonify
from backend import self as self_module  # assuming your backend is inside /backend folder
import json
import threading
import os
import subprocess
import time
from backend.move import process_emails
from backend.delete import get_old_emails, delete_emails
from backend.draft import analyze_drafts, delete_draft_by_id, delete_drafts_by_category, delete_all_drafts
from backend.unsubscribe import main, get_unique_mailing_list_senders

app = Flask(__name__)  # Flask auto-detects templates folder

# Serve the index page
@app.route("/")
def home():
    return render_template("index.html")

# Serve the login page
@app.route("/login")
def login():
    return render_template("login.html")

# Run fetch.py from Backend folder when "Continue with Google" is clicked
@app.route("/fetch-emails", methods=["GET"])
def fetch_emails():
    backend_path = os.path.join(os.getcwd(), "Backend")
    fetch_script = os.path.join(backend_path, "fetch.py")

    try:
        subprocess.run(["python", fetch_script], check=True)
        return redirect(url_for("main_page"))
    except subprocess.CalledProcessError:
        return "Error: Failed to fetch emails", 500

# Serve the main dashboard
@app.route("/main")
def main_page():
    return render_template("main.html")


@app.route("/delete")
def delete_page():
    return render_template("delete.html")

# ✅ NEW: Get senders for selected timeline
@app.route("/get_senders/<int:days>")
def get_senders(days):
    _, senders = get_old_emails(days)
    return jsonify(list(senders.keys()))

# ✅ NEW: Run delete with form data (timeline, method, etc.)
@app.route("/run_delete", methods=["POST"])
def run_delete():
    data = request.json
    days = int(data.get("days"))
    method = data.get("method")
    selected_sender = data.get("sender")
    delete_type = data.get("delete_type")

    emails, senders = get_old_emails(days)

    selected_ids = []

    if method == "all":
        selected_ids = [email["id"] for email in emails]
    elif method == "sender" and selected_sender in senders:
        selected_ids = senders[selected_sender]

    if not selected_ids:
        return jsonify({"status": "error", "message": "No emails selected."})

    delete_emails(selected_ids, delete_type)
    return jsonify({"status": "success", "message": f"Deleted {len(selected_ids)} emails."})


@app.route("/categorize")
def categorize_emails():
    try:
        # Run the script to categorize emails
        subprocess.run(["python", "backend/categorize.py"], check=True)

        # Confirm file was generated
        if os.path.exists("categorized_emails.json"):
            with open("categorized_emails.json", "r") as file:
                data = json.load(file)
            return render_template("categorize.html", emails=data)
        else:
            return "Categorization failed. JSON file not found."

    except subprocess.CalledProcessError as e:
        return f"Error running categorize.py: {str(e)}"
    

@app.route("/categorized-data")
def categorized_data():
    try:
        with open("categorized_emails.json", "r") as file:
            data = json.load(file)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": "Could not load categorized emails."}), 500
    
    
@app.route('/move-emails', methods=['POST'])
def move_emails():
    try:
        output = process_emails()  # ✅ this returns a string or list
        return jsonify({'status': 'success', 'output': output})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f"Error moving emails: {str(e)}"})


# ✅ Self-Destruct Emails Page - Show Form
@app.route("/self")
def self_page():
    service = self_module.authenticate_gmail()
    email_list = self_module.get_emails(service)
    formatted_emails = [
        {"id": email[0], "subject": email[1], "sender": email[2]} for email in email_list
    ]
    return render_template("self.html", emails=formatted_emails)

@app.route("/self-destruct", methods=["POST"])
def trigger_self_destruct():
    
    selected_ids = request.form.getlist("selected_emails")
    keywords = request.form.get("keywords", "")
    time_choice = request.form.get("time_choice", "open")
    delete_mode = request.form.get("delete_mode", "trash")
    delete_keywords = [kw.strip() for kw in keywords.split(",") if kw.strip()]

    def generate():
        service = self_module.authenticate_gmail()
        email_list = self_module.get_emails(service)
        
        selected_emails = [email for email in email_list if email[0] in selected_ids]

        yield "🚀 Self-Destruction Activated!\n"

        for email_id, subject, sender in selected_emails:
            email_info = (email_id, subject, sender)

            if not any(keyword.lower() in subject.lower() for keyword in delete_keywords):
                yield f"🚫 Email '{subject}' does not match keywords. Skipping deletion.\n"
                continue

            if time_choice == "open":
                yield f"👀 Waiting for email '{subject}' to be opened...\n"
                while not self_module.check_if_read(service, email_id):
                    time.sleep(5)
                yield f"📬 Email '{subject}' has been opened. Deleting now...\n"
            else:
                mins = int(time_choice) // 60
                yield f"⏳ Email '{subject}' will be deleted in {mins} minutes...\n"
                time.sleep(int(time_choice))

            self_module.delete_email(service, email_id, delete_mode, email_info)
            yield f"✅ Email '{subject}' from {sender} has been deleted.\n"

        # Now track future emails
        yield f"\n🔁 Tracking emails matching keywords: {', '.join(delete_keywords)}\n"
        while True:
            results = service.users().messages().list(userId="me", maxResults=10).execute()
            messages = results.get("messages", [])

            for message in messages:
                msg = service.users().messages().get(userId="me", id=message["id"]).execute()
                headers = msg["payload"]["headers"]
                subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
                sender = next((h["value"] for h in headers if h["name"] == "From"), "")

                if any(k.lower() in subject.lower() for k in delete_keywords):
                    email_info = (message["id"], subject, sender)
                    yield f"\n🚨 New email detected: '{subject}' from {sender}! Scheduled for deletion.\n"

                    if time_choice == "open":
                        yield f"👀 Waiting for email '{subject}' to be opened...\n"
                        while not self_module.check_if_read(service, message["id"]):
                            time.sleep(5)
                        yield f"📬 Email '{subject}' has been opened. Deleting now...\n"
                    else:
                        time.sleep(int(time_choice))

                    self_module.delete_email(service, message["id"], delete_mode, email_info)
                    yield f"✅ Email '{subject}' from {sender} has been deleted.\n"

            time.sleep(10)

    return Response(generate(), mimetype="text/plain")

@app.route('/draft', methods=['GET'])
def draft():
    categorized_drafts, _ = analyze_drafts()
    return render_template('draft.html', categorized=categorized_drafts)

@app.route('/delete_selected', methods=['POST'])
def delete_selected():
    data = request.get_json()
    draft_ids = data.get('draft_ids', [])

    if isinstance(draft_ids, str):  # handle single string input
        import json
        draft_ids = json.loads(draft_ids)

    if not draft_ids:
        return jsonify({'success': False, 'message': 'No drafts selected.'}), 400

    try:
        for draft_id in draft_ids:
            delete_draft_by_id(draft_id)
        return jsonify({'success': True, 'message': f'Deleted {len(draft_ids)} selected draft(s).'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    
@app.route('/delete_by_category', methods=['POST'])
def delete_by_category():
    data = request.get_json() if request.is_json else request.form
    category = data.get('category')

    if not category:
        return jsonify({'success': False, 'message': 'No category provided.'}), 400

    try:
        deleted_count = delete_drafts_by_category(category)
        return jsonify({'success': True, 'message': f'Deleted {deleted_count} draft(s) in category "{category}".'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/delete_all', methods=['POST'])
def delete_all():
    try:
        deleted_count = delete_all_drafts()
        return jsonify({'success': True, 'message': f'Deleted all ({deleted_count}) drafts.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# Serve unsubscribe.html with mailing list senders
@app.route("/unsubscribe")
def unsubscribe_page():
    senders = get_unique_mailing_list_senders()
    return render_template("unsubscribe.html", senders=senders)

# Run unsubscribe logic
@app.route("/run-unsubscribe", methods=["POST"])
def run_unsubscribe():
    selected_indices = request.form.getlist("unsubscribe")
    selected_indices = [int(i) for i in selected_indices]

    result_output = main(selected_indices).strip().split('\n')

    # Re-fetch sender list AFTER unsubscribing, which will now skip labeled ones
    updated_senders = get_unique_mailing_list_senders()
    
    return render_template("unsubscribe.html", senders=updated_senders, results=result_output)



if __name__ == "__main__":
    app.run(debug=True)
