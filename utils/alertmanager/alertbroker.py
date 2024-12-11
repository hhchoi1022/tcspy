
#%%
from tcspy.configuration import mainConfig
from tcspy.utils.alertmanager import Alert
from tcspy.utils.connector import GmailConnector
from tcspy.utils.connector import GoogleSheetConnector
from tcspy.utils.databases import DB
import datetime
import os
#%%
class AlertBroker(mainConfig):
    
    def __init__(self):
        super().__init__()
        self.googlesheet = None
        self.gmail = None
        self.DB_Daily = None
        self.alert = Alert()
    
    # Setting up the connectors
    # ==========================
    # Read & Write the alerts 
    # -----------------------
    # The term "read" means reading from the source (Astropy.Table, Google Sheet, Gmail, ...) in the telescope operating computer side 
    # The term "write" means write to the destination (Astropy.Table, Google Sheet, ...) in the broker
    # In telescope operating system, the alert is read from the Gmail, Google Sheet, or Astropy Table
    # In the broker, the alert is written to the Google Sheet, Astropy Table, or Database
    
    def _set_googlesheet(self):
        if not self.googlesheet:
            print('Setting up GoogleSheetConnector...')
            self.googlesheet = GoogleSheetConnector(spreadsheet_url = self.config['GOOGLESHEET_URL'], 
                                                    authorize_json_file = self.config['GOOGLESHEET_AUTH'],
                                                    scope = self.config['GOOGLESHEET_SCOPE'])            
            print('GoogleSheetConnector is ready.')
        else:
            pass
    
    def _set_gmail(self):
        if not self.gmail:
            print('Setting up GmailConnector...')
            self.gmail = GmailConnector(user_account = self.config['GMAIL_USERNAME'], 
                                        user_token_path = self.config['GMAIL_TOKENPATH'])
            
    def _set_DB(self):
        if not self.DB_Daily:
            print('Setting up DatabaseConnector...')
            self.DB_Daily = DB().Daily   
    
    def write_gwalert(self,
                      file_path : str, # Path of the alert file (Astropy Table readable)
                      write_type : str = 'googlesheet', # googlesheet or table
                      suffix_sheet_name : str = 'GECKO',
                      max_size : int = 200
                      ):
        """
        Sends a GW alert to the broker.
        
        Parameters:
        - file_path: str, path to the alert file
        """
        # Read the alert file
        if os.path.exists(file_path):
            try:
                alert_tbl = ascii.read(file_path)
            except:
                raise ValueError(f'Invalid file format: {file_path}')
        else:
            raise FileNotFoundError(f'File not found: {file_path}')
        
        # Decode the alert file
        alert = Alert()
        alert.decode_gwalert(alert_tbl)
        formatted_data = alert.formatted_data.copy()
        formatted_data.sort('priority')
        if max_size:
            formatted_data = formatted_data[:max_size]
        today_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        sheet_name = f'{today_str}_{suffix_sheet_name}'
        
        if write_type.upper() == 'GOOGLESHEET':
            # Send the formatted_data to GoogleSheetConnector
            print('Sending the alert to GoogleSheetConnector...')
            self._set_googlesheet()
            self.googlesheet.write_sheet(sheet_name = sheet_name, data = formatted_data)
            alert.is_sent = True
            print(f'Googlesheet saved: {sheet_name}')
            return alert
        
        elif write_type.upper() == 'TABLE':
            # Send the formatted_data to Table
            print('Sending the alert to Astropy Table...')
            current_path = os.getcwd()
            filename = sheet_name + '.ascii_fixed_width'
            filepath = os.path.join(current_path, "alert", today_str, filename)
            if not os.path.exists(os.path.dirname(filepath)):
                os.makedirs(os.path.dirname(filepath))
            formatted_data.write(filepath, format = 'ascii.fixed_width', overwrite = True)
            print(f'Astropy Table is Saved: {filepath}')
            return alert
        
        else:
            raise ValueError(f'Invalid send_type: {write_type}')

    def read_tbl(self,
                 path_tbl : str):
        pass

    def read_mail(self, 
                  mailbox : str = 'inbox',
                  since_days : int = 1,
                  alert_type : str = 'user', #user or broker
                  match_to_tiles : bool = False
                  ):
        alert = Alert()
        print('Reading the alert from GmailConnector...')
        self._set_gmail()
        try:
            if alert_type.upper() == 'USER':
                maillist = self.gmail.read_mail(mailbox = mailbox, max_emails = 10, since_days = since_days, save = True, save_dir = self.config['GMAIL_PATH'])
                if len(maillist) == 0:
                    raise ValueError('No new mail is found.')
                recent_mail_dict = maillist[-1]
                alert.decode_mail(recent_mail_dict, match_to_tiles = match_to_tiles, alert_type= alert_type )
                alert.save_history(save_dir = self.config['GMAIL_PATH'])
            elif alert_type.upper() == 'BROKER':
                maillist = self.gmail.read_mail(mailbox = mailbox, max_emails = 10, since_days = since_days, save = True, save_dir = self.config['GMAIL_PATH'])
                if len(maillist) == 0:
                    raise ValueError('No new mail is found.')

                recent_mail_dict = maillist[-1]
                alert.decode_mail(recent_mail_dict, match_to_tiles = match_to_tiles, alert_type= alert_type )
                alert.save_history(save_dir = self.config['GMAIL_SAVEPATH'])
            else:
                raise ValueError(f'Invalid alert_type: {alert_type}')
        except:
            raise RuntimeError(f'Failed to read and decode the alert')
        return alert
    
    def read_sheet(self,
                   sheet_name : str, # Sheet name
                   ):
        # Read the alert file
        alert = Alert()
        print('Reading the alert from GoogleSheetConnector...')
        self._set_googlesheet()
        try:
            alert_tbl = self.googlesheet.read_sheet(sheet_name = sheet_name)
            alert.decode_gsheet(tbl = alert_tbl)
        except:
            raise RuntimeError(f'Failed to read and decode the alert: {alert_key}')
        print('Alert is read from GoogleSheetConnector.')
        return alert
    
    def to_DB(self,
              alert : Alert):
        """
        Send the alert to the database.
        
        """
        print('Sending the alert to Database...')
        formatted_data = alert.formatted_data.copy()
        formatted_data.sort('priority')
        self._set_DB()  
        self.DB_Daily.insert(target_tbl = formatted_data)
        alert.is_inputted = True
        print(f'Targets are inserted to the database.')
        return alert
      
# %%
ab = AlertBroker()
# %%
self = ab
alert_key = '241210'
read_type = 'googlesheet'
alert_type = 'user'
max_emails = 1
mailbox = 'inbox'
# %%
