#%%
from tcspy.devices import IntegratedDevice
from tcspy.devices.integrateddevice import IntegratedDevice
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
from threading import Event
from tcspy.action.level1.devicecondition import DeviceCondition

class SlewAltAz(Interface_Runnable, Interface_Abortable):
    def __init__(self, 
                 Integrated_device : IntegratedDevice,
                 abort_action : Event):
        self.IntDevice = Integrated_device
        self.device_condition = C
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.IntDevice.unitnum, logger_name = __name__+str(self.IntDevice.unitnum)).log()
    
    def run(self,
            alt : float = None,
            az : float = None,
            **kwargs):
        if not self.abort_action.is_set():
            tel = self.IntDevice.tel  
            status = tel.get_status() 
            if status['is_stationary']:
                tel.slew_altaz(alt = float(alt), az = float(az))
            else:
                self._log.warning(f'Telescope {self.IntDevice.unitnum} is busy! Action SlewRADec is not triggered')
                pass
            self.IntDevice.update_status()
        else:
            self.abort()
            
    def abort(self):
        self.IntDevice.tel.abort()
        self.IntDevice.update_status()
        
#%%
if __name__ == '__main__':
    device = IntegratedDevice(unitnum = 2)
    s =SlewAltAz(device)
    s.run(alt=20, az= 270)    
    

# %%
