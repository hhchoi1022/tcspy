#%%
from tcspy.interfaces import *
from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from threading import Event
from tcspy.utils.logger import mainLogger
#%%
class Unpark(Interface_Runnable, Interface_Abortable):
    
    def __init__(self, 
                 Integrated_device : IntegratedDevice,
                 abort_action : Event):
        self.IDevice = Integrated_device
        self.Idevice_status = DeviceStatus(self.IDevice)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.IDevice.unitnum, logger_name = __name__+str(self.IDevice.unitnum)).log()

    def run(self):
        # Check device connection
        if self.Idevice_status.telescope.lower() == 'disconnected':
            self._log.critical(f'Telescope is disconnected. Action "{type(self).__name__}" is not triggered')
            return 
        
        # If not aborted, execute the action
        if not self.abort_action.is_set():
            self._log.info(f'[{type(self).__name__}] is triggered.')
            self.IDevice.telescope.unpark()
            if not self.abort_action.is_set():
                self._log.info(f'[{type(self).__name__}] is finished.')
            else:
                self._log.warning(f'[{type(self).__name__}] is aborted.')
        else:
            self.abort()
    
    def abort(self):
        return

#%%
if __name__ == '__main__':
    device = IntegratedDevice(unitnum = 2)
    abort_action = Event()
    s =Park(device, abort_action= abort_action)
    s.run()

# %%
