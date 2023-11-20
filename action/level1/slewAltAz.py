#%%
from tcspy.devices import IntegratedDevice
from tcspy.devices.integrateddevice import IntegratedDevice
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger


class SlewAltAz(Interface_Runnable, Interface_Abortable):
    def __init__(self, 
                 Integrated_device : IntegratedDevice):
        self.IntDevice = Integrated_device
        self._log = mainLogger(unitnum = self.IntDevice.unitnum, logger_name = __name__+str(self.IntDevice.unitnum)).log()

        
    def abort(self):
        tel = self.IntDevice.tel
        tel.abort()
        self.IntDevice.update_status()
    
    def run(self,
            alt : float = None,
            az : float = None,
            **kwargs):
        tel = self.IntDevice.tel  
        status = tel.get_status() 
        if status['is_stationary']:
            tel.slew_altaz(alt = float(alt), az = float(az))
        else:
            self._log.warning(f'Telescope {self.IntDevice.unitnum} is busy! Action SlewRADec is not triggered')
            pass
        self.IntDevice.update_status()
        
#%%
if __name__ == '__main__':
    device = IntegratedDevice(unitnum = 3)
    s =SlewAltAz(device)
    s.run(alt=40, az= 270)    
    

# %%
