# app.py
from flask import Flask, jsonify, request, render_template
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import base64
import os
import json
import time
import html
from datetime import datetime
import sentiment as 기분
import send as send_email # Renamed to avoid conflict

global_service = None
def get_service():
    global global_service
    if global_service:
        return global_service
    # Placeholder for credentials, make sure 'token.json' is available
    creds = Credentials.from_authorized_user_file("token.json", ["https://mail.google.com/"])
    global_service = build("gmail", "v1", credentials=creds)
    return global_service

def list_messages(service, label, max_results=30):
    results = service.users().messages().list(userId='me', labelIds=[label], maxResults=max_results).execute()
    messages = results.get('messages', [])
    return messages

def extract_body(payload):
    """Extract the email body from the payload"""
    body = ""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')
                break
            elif part['mimeType'] == 'text/html' and not body:
                data = part['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')
    else:
        if payload['mimeType'] == 'text/plain':
            data = payload['body']['data']
            body = base64.urlsafe_b64decode(data).decode('utf-8')
        elif payload['mimeType'] == 'text/html':
            data = payload['body']['data']
            body = base64.urlsafe_b64decode(data).decode('utf-8')
    return body

def get_message_detail(service, msg_id):
    msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
    payload = msg.get("payload", {})
    headers = payload.get("headers", [])
    subject = sender = recipient = date = ""
    for header in headers:
        name = header["name"]
        value = header["value"]
        if name == "Subject":
            subject = value
        elif name == "From":
            sender = value
        elif name == "To":
            recipient = value
        elif name == "Date":
            date = value
    body = extract_body(payload)
    snippet = html.unescape(msg.get("snippet", ""))
    
    return {
        "id": msg_id,
        "subject": subject,
        "from": sender,
        "to": recipient,
        "date": date,
        "snippet": snippet,
        "body": body
    }

def has_reply(service, message_id):
    """
    Check if a sent email has a reply in its thread.
    """
    message = service.users().messages().get(userId='me', id=message_id, format='metadata').execute()
    thread_id = message['threadId']
    thread = service.users().threads().get(userId='me', id=thread_id, format='metadata').execute()
    messages = thread.get('messages', [])
    sent_index = next((i for i, m in enumerate(messages) if m['id'] == message_id), None)
    if sent_index is None:
        return False
    return sent_index < len(messages) - 1

# --- Flask App and API Endpoints ---
app = Flask(__name__)

@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    # Fetch data for statistics
    service = get_service()
    sent_messages = list_messages(service, "SENT", max_results=100)
    inbox_messages = list_messages(service, "INBOX", max_results=100)
    
    # Simple calculation for a demo
    responses = sum(1 for msg in sent_messages if has_reply(service, msg['id']))
    emails_sent = len(sent_messages)
    response_rate = (responses / emails_sent) * 100 if emails_sent > 0 else 0
    
    # You would need to add logic to determine "pending follow-ups" more robustly
    pending_followups = sum(1 for msg in sent_messages if not has_reply(service, msg['id']))
    
    stats = {
        "emails_sent": emails_sent,
        "responses": responses,
        "response_rate": round(response_rate, 2),
        "pending_followups": pending_followups
    }
    return jsonify({"stats": stats})

@app.route('/api/emails/inbox', methods=['GET'])
def get_inbox_emails():
    service = get_service()
    inbox_messages = list_messages(service, "INBOX")
    emails = []
    for msg in inbox_messages:
        detail = get_message_detail(service, msg["id"])
        sentiment_score = 기분.get(detail['body'])
        
        quality_map = {
            'positive': {'quality': 'high', 'quality_label': 'Positive'},
            'negative': {'quality': 'low', 'quality_label': 'Negative'},
        }
        quality_info = quality_map.get(sentiment_score, {'quality': 'medium', 'quality_label': 'N/A'})
        
        emails.append({
            "sender": detail.get("from"),
            "subject": detail.get("subject"),
            "preview": detail.get("snippet"),
            "time": detail.get("date"),
            "quality": quality_info['quality'],
            "quality_label": quality_info['quality_label']
        })
    return jsonify({"recent_emails": emails})

@app.route('/api/emails/followups', methods=['GET'])
def get_followup_emails():
    service = get_service()
    sent_messages = list_messages(service, "SENT")
    follow_ups = []
    for msg in sent_messages:
        detail = get_message_detail(service, msg["id"])
        replied = has_reply(service, msg["id"])
        if not replied:
            follow_ups.append({
                "recipient": detail.get("to"),
                "subject": detail.get("subject"),
                "preview": detail.get("snippet"),
                "time": detail.get("date"),
                "quality": "low", 
                "quality_label": "Unreplied"
            })
    return jsonify({"follow_ups": follow_ups})

@app.route('/api/emails/sent', methods=['GET'])
def get_sent_emails():
    service = get_service()
    sent_messages = list_messages(service, "SENT")
    emails = []
    for msg in sent_messages:
        detail = get_message_detail(service, msg["id"])
        replied = has_reply(service, msg["id"])
        
        quality = "high" if replied else "low"
        quality_label = "Replied" if replied else "Unreplied"
        
        emails.append({
            "recipient": detail.get("to"),
            "subject": detail.get("subject"),
            "preview": detail.get("snippet"),
            "time": detail.get("date"),
            "quality": quality,
            "quality_label": quality_label
        })
    return jsonify({"sent_emails": emails})

@app.route('/api/emails/send', methods=['POST'])
def send_email_endpoint():
    data = request.get_json()
    to = data.get('to')
    print(to)
    subject = data.get('subject')
    message_body = data.get('message')

    service = get_service()
    try:
        # Assuming your send module has a createMsg and sendMsg function
        message = send_email.createMsg(to, subject, message_body)
        send_email.sendMsg(service, message)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    
@app.route('/')
def serve_dashboard():
    return render_template('index.html')

if __name__ == '__main__':
    기분.init()
    time.sleep(5)
    app.run(debug=True)