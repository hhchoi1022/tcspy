#%%
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from typing import List, Dict
import os

class GmailConnector:
    def __init__(self, user_account: str, user_token: str = None):
        self.user_account = user_account
        self.user_token = user_token
        if not user_token:
            token_path = f'{os.path.expanduser("~")}/.config/gmail/python/token_{self.user_account}.txt'
            try:
                self.user_token = open(token_path, 'r').read()
            except:
                raise ValueError(f'Error reading the token file at {token_path} or token is not provided')
        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587
        self.imap_server = 'imap.gmail.com'
        self.logged_in = False  # Track login status

    def __repr__(self):
        return f"<GmailConnector(user_account='{self.user_account}', logged_in={self.logged_in})>"

    def ensure_logged_in(self):
        """Ensure the user is logged in. If not, attempt to log in."""
        if not self.logged_in:
            print("Not logged in. Attempting to log in...")
            self.login()

    def login(self):
        """Login to the IMAP server to check credentials and set login status."""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.user_account, self.user_token)
            mail.logout()
            self.logged_in = True
            print("Login successful.")
        except Exception as e:
            self.logged_in = False
            print(f"Failed to login: {e}")
    
    def sendmail(self, to_email: str, subject: str, body: str):
        """Send an email."""
        self.ensure_logged_in()
        try:
            # Connect to the SMTP server
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.user_account, self.user_token)
            
            # Compose the email
            msg = MIMEMultipart()
            msg['From'] = self.user_account
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # Send the email
            server.sendmail(self.user_account, to_email, msg.as_string())
            server.quit()
            print("Email sent successfully.")
        except Exception as e:
            print(f"Failed to send email: {e}")
    
    def readmail(self, mailbox: str = 'inbox', max_emails: int = 10) -> List[Dict]:
        """Read emails from the specified mailbox."""
        self.ensure_logged_in()
        emails = []
        try:
            # Connect to the IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.user_account, self.user_token)
            mail.select(mailbox)
            
            # Search for all emails
            status, data = mail.search(None, 'ALL')
            email_ids = data[0].split()
            for email_id in email_ids[-max_emails:]:
                # Fetch each email
                status, data = mail.fetch(email_id, '(RFC822)')
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Parse the email
                email_data = {
                    'From': msg['From'],
                    'Subject': self._get_email_subject(msg),
                    'Date': msg['Date'],
                    'Body': self._get_email_body(msg)
                }
                emails.append(email_data)
            
            mail.logout()
        except Exception as e:
            print(f"Failed to read emails: {e}")
        return emails
    
    def deletemail(self, mailbox: str = 'inbox', subject: str = None):
        """Delete emails based on subject."""
        self.ensure_logged_in()
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.user_account, self.user_token)
            mail.select(mailbox)
            
            # Search for emails by subject
            status, data = mail.search(None, f'SUBJECT "{subject}"')
            email_ids = data[0].split()
            for email_id in email_ids:
                mail.store(email_id, '+FLAGS', '\\Deleted')
            
            mail.expunge()
            mail.logout()
            print(f"Emails with subject '{subject}' deleted successfully.")
        except Exception as e:
            print(f"Failed to delete emails: {e}")

    def _get_email_body(self, msg) -> str:
        """Extract the body from an email message."""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    return part.get_payload(decode=True).decode()
        else:
            return msg.get_payload(decode=True).decode()
        return ""
            
    def _get_email_subject(self, msg) -> str:
        """
        Extract and decode the subject of an email message.

        Args:
            msg (email.message.Message): The email message object.

        Returns:
            str: The decoded email subject.
        """
        subject = msg['Subject']
        if subject:
            decoded_parts = decode_header(subject)
            decoded_subject = ''
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    # Decode bytes using the specified encoding
                    decoded_subject += part.decode(encoding or 'utf-8', errors='ignore')
                else:
                    # If it's already a string, just append it
                    decoded_subject += part
            return decoded_subject.strip()
        return "No Subject"