
#%%
from tcspy.configuration import mainConfig
from tcspy.utils.alertmanager import AlertBroker
from tcspy.utils.alertmanager import Alert
from tcspy.utils.connector import SlackConnector
from tcspy.utils.connector import GoogleSheetConnector
import queue
import datetime
import os
import time
import numpy as np
from astropy.io import ascii
#%%

class AlertMonitor(mainConfig):
    
    def __init__(self):
        super().__init__()
        self.alertbroker = AlertBroker()
        self.slack = SlackConnector()
        self.googlesheet = GoogleSheetConnector()
        self.alert_queue = queue.Queue()
    
    def trigger_alert(self, 
                      alert : Alert,
                      send_slack : bool = True,
                      send_email : bool = True):
        tonight_str = "UTC " + datetime.datetime.now().strftime("%Y-%m-%d")
        # Insert the alert to the database
        alert = self.alertbroker.input_alert(alert)
        # Update the alert status
        alert.is_inputted = True
        self.alertbroker.save_alerthistory(alert)
        # Send the alert to the slack
        if send_slack:
            slack_message_ts = self.alertbroker.send_alertslack(alert, scheduled_time = tonight_str)
        # Send the alert via email
        if send_email:
            self.alertbroker.send_alertmail(alert, users = self.users['authorized'], scheduled_time = tonight_str, attachment = os.path.join(alert.historypath, 'alert_formatted.ascii_fixed_width'))
        
        # Wait for the alert to be updated in the database status file
        time.sleep(300)
        # Wait for the alert to be observed
        alert_targets = alert.formatted_data
        alert_observable_targets = alert_targets[alert_targets['is_observable'] == True]['id']
        DB_status_path = os.path.join(self.config['DB_STATUSPATH'], f'DB_Daily.{self.config["DB_STATUSFORMAT"]}')
        observation_status = ascii.read(DB_status_path, format = self.config['DB_STATUSFORMAT'])
        alert_observation_status = observation_status[np.isin(observation_status['id'], alert_observable_targets['id'])]
        # set the maximum waiting time for the alert to be observed
        maximum_waiting_time = 172800  # Maximum waiting time in seconds (48 hours)
        is_alert_observed = False
        while maximum_waiting_time > 0:
            time.sleep(15)
            observation_status = ascii.read(DB_status_path, format=self.config['DB_STATUSFORMAT'])
            alert_observation_status = observation_status[np.isin(observation_status['id'], alert_observable_targets['id'])]
            is_observed_each_target = [status.lower() == 'observed' for status in alert_observation_status['status']]
            is_alert_observed = all(is_observed_each_target)
            alert.num_observed_targets = sum(is_observed_each_target)
            if is_alert_observed:
                observed_time = alert_observation_status['obs_endtime']
                break
            maximum_waiting_time -= 15
        
        alert.is_observed = is_alert_observed
        self.alertbroker.save_alerthistory(alert)
        # Send the result of the alert to the email
        requester = alert.alert_sender if alert.alert_sender != '7dt.observation.broker@gmail.com' else None
        if requester:
            self.alertbroker.send_(alert = alert, users = requester, cc_users = self.users['admin'], observed_time = observed_time)
        else:
            self.alertbroker.send_resultmail(alert = alert, users = self.users['admin'], observed_time = observed_time)
        
    def check_new_mail(self,
                       mailbox = 'inbox',
                       since_days : int = 3,
                       max_numbers : int = 5,
                       match_to_tiles : bool = False,
                       match_tolerance_minutes : int = 5
                       ):
        """
        mailbox = 'inbox'
        since_days : int = 3
        max_numbers : int = 5
        match_to_tiles : bool = False
        match_tolerance_minutes : int = 5
        """
        
        alertlist = self.alertbroker.read_mail(mailbox = mailbox, since_days = since_days, max_numbers = max_numbers, match_to_tiles = match_to_tiles, match_tolerance_minutes = match_tolerance_minutes)
        if len(alertlist) < 0:
            print("No new mail found")
            return None
        
        for alert in alertlist:
            # If any new alert received, put it in the queue
            if alert.alert_sender in self.users['authorized']:
                if alert.is_inputted == False:
                    self.alert_queue.put(alert)                
                    
    def check_new_sheet(self,
                       max_numbers : int = 5,
                       ):
        sheetlist = self.googlesheet.get_sheet_list()
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
        users_dict['admin'] = self.config['ALERTBROKER_ADMINUSERS']
        return users_dict
# %%
if __name__ == "__main__":
    alertmonitor = AlertMonitor()
    #alertmonitor.check_new_mail(since_days = 3, max_numbers = 5, match_to_tiles = False, match_tolerance_minutes = 5)
    #alertmonitor.monitor_sheet()
# %%
