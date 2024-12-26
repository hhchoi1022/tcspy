
#%%
from tcspy.utils.alertmanager import AlertBroker
from tcspy.utils.connector import SlackConnector
from tcspy.utils.connector import GoogleSheetConnector
import queue
#%%

class AlertMonitor():
    
    def __init__(self):
        self.alertbroker = AlertBroker()
        self.slack = SlackConnector()
        self.googlesheet = GoogleSheetConnector()
        self.alert_queue = queue.Queue()
    
    def check_new_mail(self,
                       since_days : int = 3,
                       max_numbers : int = 5,
                       match_to_tiles : bool = False,
                       match_tolerance_minutes : int = 5
                       ):
        alertlist = self.alertbroker.read_mail(mailbox = 'inbox', since_days = since_days, max_numbers = max_numbers, match_to_tiles = match_to_tiles, match_tolerance_minutes = match_tolerance_minutes)
        if len(alertlist) < 0:
            print("No new mail found")
            return None
        
        for alert in alertlist:
            # If any new alert received, put it in the queue
            if alert.is_inputted == False:
                self.alert_queue.put(alert)                
                self.alertbroker.save_alert_info(alert = alert, save_dir = self.alertbroker.get_mail_generated_time())
                
    def monitor_sheet(self):
        sheetlist = self.googlesheet._get_sheet_list()
        if len(sheetlist) < 0:
            print("No new sheet found")
            return None
        
        for sheet_name in sheetlist:
            # If any new alert received, put it in the queue
            if not os.path.exists(os.path.join(self.config['ALERTBROKER_PATH'], 'googlesheet', sheet_name)):
                alert = self.alertbroker.read_sheet(sheet_name = sheet_name)
                if alert.is_inputted == False:
                    self.alert_queue.put(alert)                
                    self.alertbroker.save_alert_info(alert = alert, save_dir = self.alertbroker.get_sheet_generated_time())
    
    @property
    def users(self):
        users_dict = dict()
        users_dict['authorized'] = self.config['ALERTBROKER_AUTHUSERS']
        users_dict['normal'] = self.config['ALERTBROKER_NORMUSERS']
        return users_dict