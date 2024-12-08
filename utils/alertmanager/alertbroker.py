
#%%
from alertdecoder import AlertDecoder
from GSconnector import GoogleSheetConnector
from gmailconnector import GmailConnector
import datetime
import os
#%%
class AlertBroker(AlertDecoder):
    
    def __init__(self):
        super().__init__()
        self.is_sent = False
        self.googlesheet = None
        self.gmail = None
        self.DB = None
    
    def _set_googlesheet(self):
        if not self.connector.googlesheet:
            print('Setting up GoogleSheetConnector...')
            self.connector.googlesheet = GoogleSheetConnector()
            print('GoogleSheetConnector is ready.')
        else:
            pass
    
    def _set_gmail(self):
        if not self.connector.gmail:
            print('Setting up GmailConnector...')
            self.connector.gmail = GmailConnector(user_account = '7dt.observation.alert@gmail.com')
    
    def send_gwalert(self,
                     file_path : str,
                     send_type : str = 'googlesheet', # googlesheet or table or ...
                     suffix_sheet_name : str = 'GECKO',
                     max_size : int = 200
                     ):
        """
        Sends a GW alert to the broker.
        
        Parameters:
        - file_path: str, path to the alert file
        """
        # Decode the alert file
        self.decode_gwalert(file_path)
        send_data = self.formatted_data.copy()
        send_data.sort('priority')
        if max_size:
            send_data = send_data[:max_size]
        today_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        sheet_name = f'{today_str}_{suffix_sheet_name}'
        if send_type.upper() == 'GOOGLESHEET':
            # Send the formatted_data to GoogleSheetConnector
            self._set_googlesheet()
            print('Sending the alert to GoogleSheetConnector...')
            self.connector.googlesheet.write_sheet_data(sheet_name = sheet_name, data = send_data)
            self.is_sent = True
            return True
        elif send_type.upper() == 'TABLE':
            # Send the formatted_data to Table
            print('Sending the alert to Astropy Table...')
            current_path = os.getcwd()
            filename = sheet_name + '.ascii_fixed_width'
            filepath = os.path.join(current_path, "alert", today_str, filename)
            if not os.path.exists(os.path.dirname(filepath)):
                os.makedirs(os.path.dirname(filepath))
            send_data.write(filepath, format = 'ascii.fixed_width', overwrite = True)
            print(f'Saved: {filepath}')
            return True
        
    def write_gwalert(self):
        """
        Reads a GW alert from the broker.
        
        Returns:
        - alert_data: astropy.Table containing the alert data
        """
        pass
    
    def send_mailalert(self):
        
        pass
    
    def write_mailalert(self):
        pass
        
        