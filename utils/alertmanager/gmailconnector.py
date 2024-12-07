#%%
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
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
                self.user_token = open(token_path, 'r').read().strip()
                if '\xa0' in self.user_token:
                    self.user_token = self.user_token.replace('\xa0', ' ')
            except:
                raise ValueError(f'Error reading the token file at {token_path} or token is not provided')
        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587
        self.imap_server = 'imap.gmail.com'
        self.logged_in = False  # Track login status
        self.server_imap = None
        self.server_smtp = None

    def __repr__(self):
        return f"<GmailConnector(user_account='{self.user_account}', logged_in={self.logged_in})>"

    def ensure_logged_in(self):
        """Check if connections to IMAP and SMTP servers are still alive."""
        if self.server_imap:
            try:
                self.server_imap.noop()  # Send a no-operation command to test connection
            except Exception as e:
                print(f"IMAP connection lost: {e}")
                self.logged_in = False

        if self.server_smtp:
            try:
                self.server_smtp.noop()  # SMTP doesn't officially support NOOP but try a simple command
            except Exception as e:
                print(f"SMTP connection lost: {e}")
                self.logged_in = False

        if not self.logged_in:
            print("Reconnecting due to lost connections...")
            self.login()
        return True
            
    def login(self):
        """Login to the IMAP server to check credentials and set login status."""
        try:
            # Connect to the IMAP server
            self.server_imap = imaplib.IMAP4_SSL(self.imap_server)
            self.server_imap.login(self.user_account, self.user_token)
            # Connect to the SMTP server
            self.server_smtp = smtplib.SMTP(self.smtp_server, self.smtp_port)
            self.server_smtp.starttls()
            self.server_smtp.login(self.user_account, self.user_token)
            self.logged_in = True
            print("Login successful.")
        except Exception as e:
            self.logged_in = False
            print(f"Failed to login: {e}")
            
    def logout(self):
        """Gracefully close connections to IMAP and SMTP servers."""
        if self.server_imap:
            try:
                self.server_imap.logout()
                print("Logged out of IMAP server.")
            except Exception as e:
                print(f"Error logging out of IMAP server: {e}")

        if self.server_smtp:
            try:
                self.server_smtp.quit()
                print("Logged out of SMTP server.")
            except Exception as e:
                print(f"Error logging out of SMTP server: {e}")

        self.logged_in = False
    
    def sendmail(self, to_email: str, subject: str, body: str, attachments: list or str = None):
        """
        Send an email with optional attachments.
        
        Args:
            to_email (str): Recipient's email address.
            subject (str): Subject of the email.
            body (str): Body of the email.
            attachments (list or str): List of file paths to attach to the email.
        """
        self.ensure_logged_in()
        try:
            # Compose the email
            msg = MIMEMultipart()
            msg['From'] = self.user_account
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach files if any
            if attachments:
                if isinstance(attachments, str):
                    attachments = [attachments]
                for file_path in attachments:
                    try:
                        with open(file_path, "rb") as attachment:
                            # Add the attachment to the email
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)  # Encode the attachment in base64
                            # Add header info
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename={os.path.basename(file_path)}'
                            )
                            msg.attach(part)
                    except Exception as e:
                        print(f"Failed to attach file {file_path}: {e}")
            
            # Send the email
            self.server_smtp.sendmail(self.user_account, to_email, msg.as_string())
            print("Email sent successfully.")
        except Exception as e:
            print(f"Failed to send email: {e}")
    
    def readmail(self, mailbox: str = 'inbox', max_emails: int = 10, save_dir: str = "./attachments") -> List[Dict]:
        """
        Read emails and save attachments.
        
        Args:
            mailbox (str): The mailbox to read from.
            max_emails (int): The maximum number of emails to fetch.
            save_dir (str): Directory to save attachments.

        Returns:
            List[Dict]: A list of dictionaries containing email details and attachment info.
        """
        self.ensure_logged_in()
        emails = []
        
        # Ensure the directory for saving attachments exists
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        try:
            # Connect to the IMAP server
            self.server_imap.select(mailbox)
            
            # Search for all emails
            status, data = self.server_imap.search(None, 'ALL')
            email_ids = data[0].split()
            for email_id in email_ids[-max_emails:]:
                # Fetch each email
                status, data = self.server_imap.fetch(email_id, '(RFC822)')
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Parse the email
                email_data = {
                    'From': msg['From'],
                    'Subject': self._get_email_subject(msg),
                    'Date': msg['Date'],
                    'Body': self._get_email_body(msg),
                    'Attachments': []  # To store attachment info
                }

                # Check for attachments
                if msg.is_multipart():
                    for part in msg.walk():
                        content_disposition = part.get("Content-Disposition", "")
                        if "attachment" in content_disposition:
                            # Get the filename
                            filename = part.get_filename()
                            if filename:
                                # Decode the filename
                                filename = decode_header(filename)[0][0]
                                if isinstance(filename, bytes):
                                    filename = filename.decode()
                                
                                # Save the file
                                file_path = os.path.join(save_dir, filename)
                                with open(file_path, "wb") as f:
                                    f.write(part.get_payload(decode=True))
                                
                                # Append attachment info
                                email_data['Attachments'].append(file_path)

                emails.append(email_data)
            
        except Exception as e:
            print(f"Failed to read emails: {e}")
        
        return emails
    
    def deletemail(self, mailbox: str = 'inbox', subject: str = None):
        """Delete emails based on subject."""
        self.ensure_logged_in()
        try:
            self.server_imap.select(mailbox)
            
            # Search for emails by subject
            status, data = self.server_imap.search(None, f'SUBJECT "{subject}"')
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
                    # If iti's already a string, just append it
                    decoded_subject += part
            return decoded_subject.strip()
        return "No Subject"
# %%
g = GmailConnector('7dt.observation.alert@gmail.com')
# %%
g.login()
# %%
