
#%%
from tcspy.configuration import mainConfig
from tcspy.utils.alertmanager import Alert
from tcspy.utils.connector import GmailConnector
from tcspy.utils.connector import GoogleSheetConnector
from tcspy.utils.databases import DB
from astropy.table import Table
from astropy.time import Time
from datetime import datetime, timezone
import os, json
from typing import List
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
    
    def save_alert_info(self, 
                        alert : Alert,
                        alert_key : str = None):
        if not alert.alert_data:
            raise ValueError('The alert data is not read or received yet')
        
        dirname = os.path.join(self.config['ALERTBROKER_PATH'], alert.alert_type, alert_key)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        # Save alert_data
        if alert.alert_data:
            with open(os.path.join(dirname, 'alert_data.json'), 'w') as f:
                json.dump(alert.alert_data, f, indent = 4)

        # Save formatted_data
        if alert.formatted_data:
            alert.formatted_data.write(os.path.join(dirname, 'alert_formatted.ascii_fixed_width'), format = 'ascii.fixed_width', overwrite = True)
        
        # Save the alert status as json
        alert_status = dict()
        alert_status['update_time'] = Time.now().isot
        alert_status['is_decoded'] = alert.is_decoded
        alert_status['is_inputted'] = alert.is_inputted
        alert_status['is_matched_to_tiles'] = alert.is_matched_to_tiles
        with open(os.path.join(dirname, 'alert_status.json'), 'w') as f:
            json.dump(alert_status, f, indent = 4)
        
        
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
        today_str = datetime.now().strftime('%Y%m%d_%H%M%S')
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

    def read_gwalert(self,
                     path_alert : str):
        def get_received_time():
            now = Time.now()
            now_str = now.datetime.strftime('%Y%m%d_%H%M%S')
            return now_str
        
        # Read the alert file
        alert = Alert()
        print('Reading the alert from GW localization Table...')
        try:
            alert_tbl = ascii.read(path_alert)
            alert.decode_gwalert(alert_tbl)
        except:
            raise RuntimeError(f'Failed to read and decode the alert')
        finally:
            self.save_alert_info(alert = alert, alert_key = get_received_time())
        pass
    
    def read_tbl(self,
                 path_tbl : str,
                 match_to_tiles : bool = False):
        
        def get_received_time():
            now = Time.now()
            now_str = now.datetime.strftime('%Y%m%d_%H%M%S')
            return now_str
        
        # Read the alert file
        alert = Alert()
        print('Reading the alert from Astropy Table...')
        try:
            alert_tbl = ascii.read(path_tbl)
            alert.decode_tbl(alert_tbl, match_to_tiles = match_to_tiles)
        except:
            raise RuntimeError(f'Failed to read and decode the alert')
        finally:
            self.save_alert_info(alert = alert, alert_key = get_received_time())
        pass

    def read_mail(self, 
                  mailbox : str = 'inbox',
                  since_days : int = 1,
                  max_numbers : int = 10,
                  match_to_tiles : bool = False
                  ) -> List[Alert]:
        
        def get_received_time(mail_dict):
            parsed_date = datetime.strptime(mail_dict['Date'], '%a, %d %b %Y %H:%M:%S %z')
            utc_date = parsed_date.astimezone(timezone.utc)
            date_str = utc_date.strftime('%Y%m%d_%H%M%S')
            return date_str
        
        print('Reading the alert from GmailConnector...')
        self._set_gmail()
        try:
            alertlist = []
            maillist = self.gmail.read_mail(mailbox = mailbox, max_numbers = max_numbers, since_days = since_days, save = True, save_dir = os.path.join(self.config['ALERTBROKER_PATH'], 'gmail'))
            if len(maillist) == 0:
                raise ValueError('No new mail is found.')
            else:
                for mail_dict in maillist:
                    alert = Alert()
                    try:
                        alert.decode_mail(mail_dict, match_to_tiles = match_to_tiles)
                        alertlist.append(alert)
                    except:
                        pass
                    finally:
                        self.save_alert_info(alert = alert, alert_key = get_received_time(mail_dict))
        except:
            raise RuntimeError(f'Failed to read and decode the alert')
        print('Alert is read from GmailConnector.')
        return alertlist
    
    def read_sheet(self,
                   sheet_name : str, # Sheet name
                   match_to_tiles : bool = False
                   )-> List[Alert]:
        # Read the alert file
        alert = Alert()
        print('Reading the alert from GoogleSheetConnector...')
        self._set_googlesheet()
        try:
            alert_tbl = self.googlesheet.read_sheet(sheet_name = sheet_name, format_ = 'Table', save = True, save_dir = os.path.join(self.config['ALERTBROKER_PATH'], 'googlesheet'))
            alert.decode_gsheet(tbl = alert_tbl, match_to_tiles = match_to_tiles)
        except:
            pass
        finally:
            self.save_alert_info(alert = alert, alert_key = sheet_name)
        print('Alert is read from GoogleSheetConnector.')
        return alert
    
    def send_alert_to_users(self, 
                            alert : Alert,
                            users : List[str],
                            scheduled_time : str = None,
                            attachment : str = None):
        
        def format_mail_body(alert : Alert, scheduled_time : str = None):
            target_info = alert.formatted_data
            if len(target_info) == 1:
                single_target_info = target_info[0]
                single_target_head =  "<p>Dear 7DT users, </p>"
                single_target_head += "<p>Single alert is received from the user: %s.</p>" %alert.alert_sender
                if scheduled_time:
                    single_target_head += "<p>The observation is scheduled at(on) <b><code>%s</code></b>.</p>" %scheduled_time
                single_target_head += "<p>Please check below observation information.</p>"
                
                single_target_targetinfo_body = "<p><strong>===== Target Information =====</strong></p>"
                single_target_targetinfo_body += "<p><b>Name:</b> %s </p>" %single_target_info['objname']
                single_target_targetinfo_body += "<p><b>RA:</b> %.5f </p>" %single_target_info['RA']
                single_target_targetinfo_body += "<p><b>Dec:</b> %.5f </p>" %single_target_info['De']
                single_target_targetinfo_body += "<p><b>Priority:</b> %d </p>" %single_target_info['priority']  
                single_target_targetinfo_body += "<p><b>Immediate start?:</b> %s </p>" %str(bool(single_target_info['is_ToO']))
                single_target_targetinfo_body += "<p><b>ID:</b> %s </p>" %single_target_info['id']  
                if single_target_info['note']:
                    single_target_targetinfo_body += "<p><b>Note:</b> %s </p>" %single_target_info['note']
                if single_target_info['comments']:
                    single_target_targetinfo_body += "<p><b>Comments:</b> %s </p>" %single_target_info['comments']
                if single_target_info['obs_starttime']:
                    single_target_targetinfo_body += "<p><b>Requested obstime:</b> %s </p>" %single_target_info['obs_starttime']
                if alert.is_matched_to_tiles:
                    single_target_targetinfo_body += "<span style='color: red;'><p><b>[This target is matched to the 7DS RIS tiles. The target name is stored in 'Note'] </p></b></span>"
                single_target_targetinfo_box = f"""
                <div style="
                    border: 3px solid red;
                    padding: 15px;
                    margin: 10px;
                    background-color: #FFFAF0;
                    border-radius: 10px;
                    width: 500px;
                    text-align: left;
                ">
                    <p>{single_target_targetinfo_body}</p>
                </div>
                """
                
                single_target_expinfo_body = "<p><strong>===== Exposure Information =====</p></strong>"
                single_target_expinfo_body += "<p><b>Exposure time:</b> %.1fs x %d </p>" %(single_target_info['exptime'], single_target_info['count'])
                single_target_expinfo_body += "<p><b>Obsmode:</b> %s </p>" %single_target_info['obsmode']
                if single_target_info['obsmode'].lower() == 'spec':
                    single_target_expinfo_body += "<p><b>Specmode:</b> %s </p>" %single_target_info['specmode']
                elif single_target_info['obsmode'].lower() == 'deep':
                    single_target_expinfo_body += "<p><b>Filter:</b> %s </p>" %single_target_info['filter']
                    single_target_expinfo_body += "<p><b>Number of telescope:</b> %d </p>" %single_target_info['ntelescope']
                else:
                    single_target_expinfo_body += "<p><b>Filter:</b> %s </p>" %single_target_info['filter']
                single_target_expinfo_body += "<p><b>Gain:</b> %s </p>" %single_target_info['gain']
                single_target_expinfo_body += "<p><b>Binning:</b> %s </p>" %single_target_info['binning']
                
                single_target_expinfo_box = f"""
                <div style="
                    border: 3px solid blue;
                    padding: 15px;
                    margin: 10px;
                    background-color: #FFFAF0;
                    border-radius: 10px;
                    width: 500px;
                    text-align: left;
                ">
                    <p>{single_target_expinfo_body}</p>
                </div>
                """
                
                single_target_tail = "<p> Best regards, </p>"
                single_target_tail += "Hyeonho Choi"
                single_target_text = single_target_head + single_target_targetinfo_box + single_target_expinfo_box + single_target_tail
                return single_target_text
            else:
                multi_target_info = target_info
                multi_target_head =  "<p>Dear 7DT users, </p>"
                multi_target_head += f"<p>Multiple alerts are received from the user: %s.</p>" %alert.alert_sender
                if scheduled_time:
                    multi_target_head += "<p>The observation is scheduled at(on) <b><code>%s</code></b>.</p>" %scheduled_time
                multi_target_head += "<p>Please check below observation information.</p>"
                
                multi_target_targetinfo_body = "<p><strong>===== Target Information =====</strong></p>"
                multi_target_targetinfo_body += "<p><b>Number of targets:</b> %s </p>" %len(multi_target_info)
                multi_target_targetinfo_body += "<p><b>Filters:</b> %s </p>" %list(set(multi_target_info['filter']))  
                multi_target_targetinfo_body += "<p><b>Immediate start?:</b> %s </p>" %str(bool(multi_target_info['is_ToO']))
                # Attachment 
                
                
    
    def to_DB(self,
              alert : List[Alert],
              do_alert_to_users : bool = False):
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
    
    @property
    def users(self):
        users_dict = dict()
        users_dict['authorized'] = self.config['ALERTBROKER_AUTHUSERS']
        users_dict['normal'] = self.config['ALERTBROKER_NORMUSERS']
        return users_dict
      
# %%
if __name__ == '__main__':
    self = AlertBroker()
    since_days = 3
    max_numbers = 5
    match_to_tiles = True
    from tcspy.utils.connector import GmailConnector
    G = GmailConnector('7dt.observation.alert@gmail.com')
    #G.login()
    mail_str = G.read_mail()
#%%
if __name__ == '__main__':
    alert = Alert()
    alert.decode_mail(mail_str[0], match_to_tiles = True)
    print(alert.formatted_data)
# %%
