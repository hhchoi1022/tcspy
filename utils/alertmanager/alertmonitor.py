
#%%
from utils.alertbroker.alertbroker import AlertBroker
from utils.connector.slackconnector import SlackConnector
#%%

class AlertMonitor():
    
    
    def __init__(self):
        self.alertbroker = AlertBroker()
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