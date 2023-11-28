#%%
from tcspy.devices import IntegratedDevice
from tcspy.devices.integrateddevice import IntegratedDevice
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
from threading import Event
from tcspy.devices import DeviceStatus

class SlewAltAz(Interface_Runnable, Interface_Abortable):
    def __init__(self, 
                 Integrated_device : IntegratedDevice,
                 abort_action : Event):
        self.IntDevice = Integrated_device
        self.IntDevice_status = DeviceStatus(self.IntDevice)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.IntDevice.unitnum, logger_name = __name__+str(self.IntDevice.unitnum)).log()
    
    def run(self,
            alt : float = None,
            az : float = None,
            **kwargs):
        if not self.abort_action.is_set():
            tel = self.IntDevice.tel  
            status = self.IntDevice_status.telescope
            if status.lower() == 'disconnected':
                self._log.critical(f'Telescope is disconnected. Action "{type(self).__name__}" is not triggered')
            elif status.lower() == 'parked' :
                self._log.warning(f'Telescope is parked. Unpark before operation')
            elif status.lower() == 'busy':
                self._log.warning(f'Telescope {self.IntDevice.unitnum} is busy! Action SlewRADec is not triggered')
            else:
                tel.slew_altaz(alt = float(alt), az = float(az))
        else:
            self.abort()
            
    def abort(self):
        self.IntDevice.tel.abort()
        self.IntDevice.update_status()
        
#%%
if __name__ == '__main__':
    device = IntegratedDevice(unitnum = 1)
    abort_action = Event()
    s =SlewAltAz(device, abort_action)
    s.run(alt=20, az= 270)    
    

# %%
