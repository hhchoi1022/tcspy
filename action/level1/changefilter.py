#%%
from tcspy.interfaces import *
from tcspy.devices import IntegratedDevice
from threading import Thread, Event

class ChangeFilter(Interface_Runnable, Interface_Abortable):
    
    def __init__(self, 
                 Integrated_device : IntegratedDevice,
                 abort_action : Event = None):
        self.IntDevice = Integrated_device
        self.abort_action = abort_action
    
    def run(self,
            filter_ : str):
        if not self.abort_action.is_set():
            #if not self.IntDevice.filt.status['filter'] == filter_:
            self.IntDevice.filt.move(filter_ = filter_)
        else:
            self.abort()
    
    def abort(self):
        self.IntDevice.filt.abort()