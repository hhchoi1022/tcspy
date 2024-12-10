
#%%
from tcspy.utils.alertmanager import Alert
from tcspy.utils.connector import SlackConnector
#%%

class AlertMonitor():
    
    
    def __init__(self):
        self.alertbroker = Alert()
        self.slackconnector = SlackConnector()
        self.is_sent = False
        self.is_posted = False
        self.is_alerted = False
        self.is_connected = False
        self.is_monitored = False
        self.is_observed = False
        self.is_reported = False
        self.is_retrieved = False
        self.is_saved = False
        self.is_submitted = False