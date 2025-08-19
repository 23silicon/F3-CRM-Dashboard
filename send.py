from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import base64
from email.mime.text import MIMEText
import time

def createMsg(to, subject, body_text):
    """Create a MIMEText email message"""
    message = MIMEText(body_text)
    message['to'] = to
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}


def createReply(original_message, reply_text):
    message = MIMEText(reply_text)
    message['to'] = original_message['from']
    message['subject'] = "Re: " + original_message['subject']
    message['In-Reply-To'] = original_message['id']
    message['References'] = original_message['id']
    
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    return {
        'raw': raw_message,
        'threadId': original_message['threadId']
    }


def sendMsg(service, message):
    """Send an email via Gmail API"""
    sent_msg = service.users().messages().send(userId='me', body=message).execute()
    return sent_msg

def scheduleSend(service, message, timestamp):
    #time.time() gives current time, add #seconds (int) to schedule into the future
    """
    Schedule an email to be sent at a future time.
    send_at_timestamp: UNIX timestamp (seconds since epoch)
    """
    # If the scheduled time is in the past, send immediately
    if time.time() >= timestamp:
        return sendMsg(service, message)
    
    # Otherwise, create a draft for future sending
    draft = service.users().drafts().create(userId='me', body={'message': message}).execute()
    print(f"Draft created with ID: {draft['id']}. Send at {time.ctime(timestamp)}")
    return draft