#%%
from threading import Event

from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger

class SlewRADec(Interface_Runnable, Interface_Abortable):
    def __init__(self, 
                 Integrated_device : IntegratedDevice,
                 abort_action : Event):
        self.IDevice = Integrated_device
        self.IDevice_status = DeviceStatus(self.IDevice)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.IDevice.unitnum, logger_name = __name__+str(self.IDevice.unitnum)).log()
    
    def run(self,
            ra : float = None,
            dec : float = None,
            **kwargs):
        
        # Check device connection
        telescope = self.IDevice.telescope
        status_telescope = self.IDevice_status.telescope.lower()
        if status_telescope == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: telescope is disconnected.')
            return False

        # Check abort_action
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            return False
        
        # Start action
        self._log.info(f'[{type(self).__name__}] is triggered.')
        if status_telescope == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: telescope is disconnected.')
            return False
        elif status_telescope == 'parked' :
            self._log.critical(f'[{type(self).__name__}] is failed: telescope is parked.')
            return False
        elif status_telescope == 'busy':
            self._log.critical(f'[{type(self).__name__}] is failed: telescope is busy.')
            return False
        else:
            result_slew = telescope.slew_radec(ra = float(ra),
                                               dec = float(dec),
                                               abort_action = self.abort_action,
                                               tracking = True)
        
        if result_slew:
            self._log.info(f'[{type(self).__name__}] is finished.')
        else:
            self._log.critical(f'[{type(self).__name__}] is failed: telescope slew_radec failure.')
            return False
        return True
    
    # For faster trigger of abort action
    def abort(self):
        status_telescope = self.IDevice_status.telescope.lower()
        if status_telescope == 'busy':
            self.IDevice.telescope.abort()
        else:
            pass   
#%%
if __name__ == '__main__':
    device = IntegratedDevice(unitnum = 2)
    abort_action = Event()
    s =SlewRADec(device, abort_action= abort_action)
    s.run(ra = 0, dec= 50)
    device.tel.slew_altaz(alt = 30, az = 270)
    

# %%
