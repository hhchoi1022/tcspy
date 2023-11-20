#%%
from tcspy.interfaces import *
from tcspy.devices import IntegratedDevice

class ChangeFilter(Interface_Runnable, Interface_Abortable):
    
    def __init__(self, 
                 Integrated_device : IntegratedDevice):
        self.IntDevice = Integrated_device
    
    def run(self,
            filter_ : str):
        if not self.IntDevice.filt.status['filter'] == filter_:
            self.IntDevice.filt.move(filter_ = filter_)
    
    def abort(self):
        self.IntDevice.filt.abort()