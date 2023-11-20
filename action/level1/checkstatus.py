#%%
from tcspy.interfaces import *
from tcspy.devices import IntegratedDevice

class CheckStatus(Interface_Runnable):
    
    def __init__(self, 
                 Integrated_device : IntegratedDevice):
        self.IntDevice = Integrated_device
    
    def run(self):
        return self.IntDevice.status

