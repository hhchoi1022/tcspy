#%%
from threading import Event

from tcspy.devices import IntegratedDevice
from tcspy.devices.integrateddevice import IntegratedDevice
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
from tcspy.devices import DeviceStatus

class SlewAltAz(Interface_Runnable, Interface_Abortable):
    def __init__(self, 
                 Integrated_device : IntegratedDevice,
                 abort_action : Event):
        self.IDevice = Integrated_device
        self.IDevice_status = DeviceStatus(self.IDevice)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.IDevice.unitnum, logger_name = __name__+str(self.IDevice.unitnum)).log()
    
    def run(self,
            alt : float = None,
            az : float = None,
            **kwargs):
        tel = self.IDevice.telescope  
        status_tel = self.IDevice_status.telescope
        # Check device connection
        if status_tel.lower() == 'disconnected':
            self._log.critical(f'Telescope is disconnected. Action "{type(self).__name__}" is not triggered')
            return

        # If not aborted, execute the action
        if not self.abort_action.is_set():
            self._log.info(f'[{type(self).__name__}] is triggered.')
            if status_tel.lower() == 'disconnected':
                self._log.critical(f'Telescope is disconnected. Action "{type(self).__name__}" is not triggered')
            elif status_tel.lower() == 'parked' :
                self._log.warning(f'Telescope is parked. Unpark before operation')
            elif status_tel.lower() == 'busy':
                self._log.warning(f'Telescope {self.IDevice.unitnum} is busy! Action SlewRADec is not triggered')
            else:
                tel.slew_altaz(alt = float(alt),
                               az = float(az),
                               abort_action = self.abort_action,
                               tracking = False)
            if not self.abort_action.is_set():
                self._log.info(f'[{type(self).__name__}] is finished.')
            else:
                self._log.warning(f'[{type(self).__name__}] is aborted.')
        else:
            self.abort()
            
    def abort(self):
        status_telescope = self.IDevice_status.telescope.lower()
        if status_telescope == 'disconnected':
            self._log.critical(f'Telescope is disconnected. Action "{type(self).__name__}" is not aborted')
            return 
        elif status_telescope == 'busy':
            self.IDevice.telescope.abort()
        else:
            pass 
#%%
if __name__ == '__main__':
    device = IntegratedDevice(unitnum = 2)
    abort_action = Event()
    s =SlewAltAz(device, abort_action)
    s.run(alt=40, az= 270)    
    

# %%
