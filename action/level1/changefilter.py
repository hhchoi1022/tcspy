#%%
from tcspy.interfaces import *
from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from threading import Event
from tcspy.utils.logger import mainLogger
#%%

class ChangeFilter(Interface_Runnable, Interface_Abortable):
    
    def __init__(self, 
                 Integrated_device : IntegratedDevice,
                 abort_action : Event):
        self.IDevice = Integrated_device
        self.Idevice_status = DeviceStatus(self.IDevice)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.IDevice.unitnum, logger_name = __name__+str(self.IDevice.unitnum)).log()

    def run(self,
            filter_ : str):
        if not self.abort_action.is_set():
            if self.Idevice_status.filterwheel.lower() == 'disconnected':
                self._log.critical(f'Filterwheel is disconnected. Action "{type(self).__name__}" is not triggered')
            else:
                if self.Idevice_status.filterwheel.lower() == 'idle':
                    self.IDevice.filt.move(filter_ = filter_)
        else:
            self.abort()
    
    def abort(self):
        self.IDevice.filt.abort()
