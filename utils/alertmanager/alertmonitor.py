
#%%
from tcspy.utils.alertmanager import AlertBroker
from tcspy.utils.connector import SlackConnector
#%%

class AlertMonitor():
    
    def __init__(self):
        self.alertbroker = AlertBroker()
        self.slack = SlackConnector()
    
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
        
        new_alertlist = []
        for alert in alertlist:
            if alert.is_inputted == False:
                new_alertlist.append(alert)
                alert.is_inputted = True
                
                self.alertbroker.save_alert_info(alert = alert, save_dir = self.alertbroker.get_mail_generated_time())
            
        
        alerts = self.alertbroker.get_alerts()
        for alert in alerts:
            self.slack.send_message(alert)
        return alerts
    
    def monitor_sheet(self):
        alerts = self.alertbroker.get_alerts()
        for alert in alerts:
            self.slack.send_message(alert)
        return alerts
    
    @property
    def users(self):
        users_dict = dict()
        users_dict['authorized'] = self.config['ALERTBROKER_AUTHUSERS']
        users_dict['normal'] = self.config['ALERTBROKER_NORMUSERS']
        return users_dict