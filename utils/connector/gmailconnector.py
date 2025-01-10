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
from datetime import datetime, timedelta, timezone
import json

class GmailConnector:
    def __init__(self, user_account: str, user_token_path: str = None):
        self.user_account = user_account
        self.user_token_path = user_token_path
        self.user_token = None
        if not user_token_path:
            self.user_token_path = f'{os.path.expanduser("~")}/.config/gmail/python/token_{self.user_account}.txt'
        try:
            self.user_token = open(self.user_token_path, 'r').read().strip()
            if '\xa0' in self.user_token:
                self.user_token = self.user_token.replace('\xa0', ' ')
        except:
            raise ValueError(f'Error reading the token file at {self.user_token_path} or token is not provided')
        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587
        self.imap_server = 'imap.gmail.com'
        self.logged_in_imap = False  # Track login status
        self.logged_in_smtp = False  # Track login status
        self.server_imap = None
        self.server_smtp = None

    def __repr__(self):
        return f"<GmailConnector(user_account='{self.user_account}', logged_in={self.logged_in})>"

    def ensure_logged_in_imap(self):
        """Check if connections to IMAP servers are still alive."""
        if self.server_imap:
            try:
                self.server_imap.noop()  # Send a no-operation command to test connection
            except Exception as e:
                print(f"IMAP connection lost: {e}")
                self.logged_in_imap = False

        if not self.logged_in_imap:
            print("The account is not logged in. Try login...")
            self.login_imap()
        return True
    
    def ensure_logged_in_smtp(self):
        """Check if connections to SMTP servers are still alive."""
        if self.server_smtp:
            try:
                self.server_smtp.noop()  # SMTP doesn't officially support NOOP but try a simple command
            except Exception as e:
                print(f"SMTP connection lost: {e}")
                self.logged_in_smtp = False

        if not self.logged_in_smtp:
            print("The account is not logged in. Try login...")
            self.login_smtp()
        return True

    def login_imap(self):
        """Login to the IMAP server to check credentials and set login status."""
        try:
            # Connect to the IMAP server
            self.server_imap = imaplib.IMAP4_SSL(self.imap_server)
            self.server_imap.login(self.user_account, self.user_token)
            self.logged_in_imap = True
            print("IMAP Login successful.")
        except Exception as e:
            self.logged_in_imap = False
            print(f"Failed to login IMAP: {e}")
            
    def login_smtp(self):
        """Login to the IMAP server to check credentials and set login status."""
        try:

            # Connect to the SMTP server
            self.server_smtp = smtplib.SMTP(self.smtp_server, self.smtp_port)
            self.server_smtp.starttls()
            self.server_smtp.login(self.user_account, self.user_token)
            self.logged_in_smtp = True
            print("SMTP Login successful.")
        except Exception as e:
            self.logged_in_smtp = False
            print(f"Failed to login SMTP: {e}")
            
    def logout_imap(self):
        """Gracefully close connections to IMAP and SMTP servers."""
        if self.server_imap:
            try:
                self.server_imap.logout()
                print("Logged out of IMAP server.")
            except Exception as e:
                print(f"Error logging out of IMAP server: {e}")

        self.logged_in_imap = False
        
    def logout_smtp(self):
        """Gracefully close connections to IMAP and SMTP servers."""
        if self.server_smtp:
            try:
                self.server_smtp.quit()
                print("Logged out of SMTP server.")
            except Exception as e:
                print(f"Error logging out of SMTP server: {e}")

        self.logged_in_smtp = False
    
    def send_mail(self, to_users: str or list, cc_users : str or list, subject: str, body: str, attachments: list or str = None, text_type = 'plain'):
        """
        Send an email with optional attachments.
        
        Args:
            to_users (str or list): Recipient's email address.
            cc_users (str or list): CC recipient's email address.
            subject (str): Subject of the email.
            body (str): Body of the email.
            attachments (list or str): List of file paths to attach to the email.
        """
        if text_type not in ['plain', 'html']:
            raise ValueError("Invalid text_type. Must be 'plain' or 'html'.")
        self.ensure_logged_in_smtp()
        try:
            # Convert to_users and cc_users to lists if they are strings
            if isinstance(to_users, str):
                to_users = [to_users]
            if isinstance(cc_users, str):
                cc_users = [cc_users]

            # Compose the email
            msg = MIMEMultipart()
            msg['From'] = self.user_account
            msg['To'] = ", ".join(to_users)  # Display multiple recipients
            msg['Subject'] = subject
            if cc_users:
                msg['CC'] = ", ".join(cc_users)
            msg.attach(MIMEText(body, text_type))

            # Attach files if any
            if attachments:
                if isinstance(attachments, str):
                    attachments = [attachments]
                for file_path in attachments:
                    try:
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename={os.path.basename(file_path)}'
                            )
                            msg.attach(part)
                    except Exception as e:
                        print(f"Failed to attach file {file_path}: {e}")

            # Combine all recipients (To + CC)
            all_recipients = to_users
            if cc_users:
                all_recipients += cc_users

            # Send the email
            try:
                self.server_smtp.sendmail(self.user_account, all_recipients, msg.as_string())
            except:
                print('Sending email failed. Try to login again...')
                self.login_smtp()
                time.sleep(5)
                self.server_smtp.sendmail(self.user_account, all_recipients, msg.as_string())
            # Logout of the SMTP server
            self.logout_smtp()
            print("Email sent successfully.")
        except Exception as e:
            print(f"Failed to send email: {e}")
    
    def read_mail(self, mailbox: str = 'inbox', max_numbers: int = 10, since_days : float = 5, save : bool = True, save_dir : str = '../alert_history/gmail') -> List[Dict]:
        """
        Read emails and save attachments.
        
        Args:
            mailbox (str): The mailbox to read from.
            max_numbers (int): The maximum number of emails to fetch.
            save_dir (str): Directory to save attachments.

        Returns:
            List[Dict]: A list of dictionaries containing email details and attachment info.
        """
        
        # Function to extract and decode the 'From' field
        def get_sender_email(mail_from):
            # Parse the 'From' field
            if '<' in mail_from and '>' in mail_from:
                # Separate name and email
                name, email_address = mail_from.split('<')
                email_address = email_address.strip('>')
                
                # Decode the name part if it's encoded
                decoded_name, encoding = decode_header(name.strip())[0]
                if isinstance(decoded_name, bytes):  # Decode bytes if necessary
                    decoded_name = decoded_name.decode(encoding or 'utf-8')
                return decoded_name, email_address
            else:
                return None, mail_from
        
        self.ensure_logged_in_imap()
        emails = []
        
        try:
            # Connect to the IMAP server
            self.server_imap.select(mailbox)
            
            # Search for all emails
            search_criteria = 'ALL'
            if since_days:
                since_time = datetime.utcnow() - timedelta(days=since_days)
                since_date = since_time.strftime('%d-%b-%Y')
                search_criteria = f'(SINCE "{since_date}")'

            status, data = self.server_imap.search(None, search_criteria)
            email_ids = data[0].split()
            for email_id in email_ids[-max_numbers:]:
                # Fetch each email
                status, data = self.server_imap.fetch(email_id, '(RFC822)')
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Parse the email
                email_data = {
                    'From': get_sender_email(msg['From']),
                    'Subject': self._get_email_subject(msg),
                    'Date': msg['Date'],
                    'Body': self._get_email_body(msg),
                    'Attachments': []  # To store attachment info
                }
                
                parsed_date = datetime.strptime(email_data['Date'], '%a, %d %b %Y %H:%M:%S %z')
                utc_date = parsed_date.astimezone(timezone.utc)
                date_str = utc_date.strftime('%Y%m%d_%H%M%S')
                
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
                                if save:
                                    save_dir_for_attachments = os.path.join(save_dir, date_str, 'attachments')
                                    if not os.path.exists(save_dir_for_attachments):        
                                        os.makedirs(save_dir_for_attachments)
                                    attachment_path = os.path.join(save_dir_for_attachments, filename)
                                    with open(attachment_path, "wb") as f:
                                        f.write(part.get_payload(decode=True))
                                    # Append attachment info
                                    email_data['Attachments'].append(attachment_path)
                if save:
                    save_dir_for_email = os.path.join(save_dir, date_str)
                    if not os.path.exists(save_dir_for_email):
                        os.makedirs(save_dir_for_email)
                    email_path = os.path.join(save_dir_for_email, "body.txt")
                    with open(email_path, "w") as f:
                        json.dump(email_data, f, indent = 4)

                emails.append(email_data)
            
        except Exception as e:
            print(f"Failed to read emails: {e}")
        
        return emails
    
    def delete_mail(self, mailbox: str = 'inbox', subject: str = None):
        """Delete emails based on subject."""
        self.ensure_logged_in()
        try:
            self.server_imap.select(mailbox)
            
            # Search for emails by subject
            status, data = self.server_imap.search(None, f'SUBJECT "{subject}"')
            email_ids = data[0].split()
            for email_id in email_ids:
                self.server_imap.store(email_id, '+FLAGS', '\\Deleted')
            
            self.server_imap.expunge()
            self.server_imap.logout()
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
