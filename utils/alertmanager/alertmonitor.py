
#%%
from tcspy.configuration import mainConfig
from tcspy.utils.alertmanager import AlertBroker
from tcspy.utils.connector import SlackConnector
from tcspy.utils.connector import GoogleSheetConnector
import queue
import os
#%%

class AlertMonitor(mainConfig):
    
    def __init__(self):
        super().__init__()
        self.alertbroker = AlertBroker()
        self.slack = SlackConnector()
        self.googlesheet = GoogleSheetConnector()
        self.alert_queue = queue.Queue()
    
    def check_new_mail(self,
                       mailbox = 'inbox',
                       since_days : int = 3,
                       max_numbers : int = 5,
                       match_to_tiles : bool = False,
                       match_tolerance_minutes : int = 5
                       ):
        alertlist = self.alertbroker.read_mail(mailbox = mailbox, since_days = since_days, max_numbers = max_numbers, match_to_tiles = match_to_tiles, match_tolerance_minutes = match_tolerance_minutes)
        if len(alertlist) < 0:
            print("No new mail found")
            return None
        
        for alert in alertlist:
            # If any new alert received, put it in the queue
            if alert.is_inputted == False:
                self.alert_queue.put(alert)                
                
    def check_new_sheet(self,
                       max_numbers : int = 5,
                       ):
        sheetlist = self.googlesheet._get_sheet_list()
        # Remove the sheet that contains "format" or "readme" in the name
        sheetlist = [sheet_name for sheet_name in sheetlist if "format" not in sheet_name.lower() and "readme" not in sheet_name.lower()]
        if len(sheetlist) < 0:
            print("No new sheet found")
            return None
        # From the most recent sheet
        sheetlist.reverse()
        for sheet_name in sheetlist[:max_numbers]:
            # If any new alert received, put it in the queue
            alert = self.alertbroker.read_sheet(sheet_name = sheet_name)
            if alert.is_inputted == False:
                self.alert_queue.put(alert)                
    
    @property
    def users(self):
        users_dict = dict()
        users_dict['authorized'] = self.config['ALERTBROKER_AUTHUSERS']
        users_dict['normal'] = self.config['ALERTBROKER_NORMUSERS']
        return users_dict
# %%
if __name__ == "__main__":
    alertmonitor = AlertMonitor()
    #alertmonitor.check_new_mail(since_days = 3, max_numbers = 5, match_to_tiles = False, match_tolerance_minutes = 5)
    #alertmonitor.monitor_sheet()
# %%
