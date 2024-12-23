
#%%
from tcspy.utils.alertmanager import AlertBroker
from tcspy.utils.connector import SlackConnector
#%%

class AlertMonitor():
    
    
    def __init__(self):
        self.alertbroker = AlertBroker()
        self.slack = SlackConnector()
        
    @property
    def users(self):
        users_dict = dict()
        users_dict['authorized'] = self.config['ALERTBROKER_AUTHUSERS']
        users_dict['normal'] = self.config['ALERTBROKER_NORMUSERS']
        return users_dict