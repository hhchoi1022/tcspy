#%%
from tcspy.interfaces import *
from tcspy.devices import IntegratedDevice

class Filterchange(Interface_Filterchange):
    
    def __init__(self, 
                 Integrated_device : IntegratedDevice):
        self.IntDevice = Integrated_device
    
    def change_filter(self,
                      filter_ : str):
        self.IntDevice.filt.move(filter_ = filter_)
    
    def abort(self):
        self.IntDevice.filt.abort()