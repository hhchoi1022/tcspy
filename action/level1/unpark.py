#%%
from threading import Event

from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from tcspy.utils.logger import mainLogger
from tcspy.interfaces import *
from tcspy.utils.exception import *

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
        self._log.info(f'[{type(self).__name__}] is triggered.')
        status_telescope = self.Idevice_status.telescope.lower()
        if status_telescope == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: telescope is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: telescope is disconnected.')

        # Start action
        if status_telescope == 'busy':
            self._log.critical(f'[{type(self).__name__}] is failed: telescope is busy.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: telescope is busy.')
        else:
            try:
                result_unpark = self.IDevice.telescope.unpark()
            except ParkingFailedException:
                self._log.info(f'[{type(self).__name__}] is finished.')
                self._log.critical(f'[{type(self).__name__}] is failed')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: telescope unpark failure.')
                
        if result_unpark:
            self._log.info(f'[{type(self).__name__}] is finished.')
        return True
    
    def abort(self):
        return

#%%
if __name__ == '__main__':
    device = IntegratedDevice(unitnum = 2)
    abort_action = Event()
    s =Unpark(device, abort_action= abort_action)
    s.run()

# %%
