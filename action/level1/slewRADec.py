#%%
from tcspy.devices import IntegratedDevice
from tcspy.devices.integrateddevice import IntegratedDevice
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger

class SlewRADec(Interface_Runnable, Interface_Abortable):
    def __init__(self, 
                 Integrated_device : IntegratedDevice):
        self.IntDevice = Integrated_device
        self._log = mainLogger(unitnum = self.IntDevice.unitnum, logger_name = __name__+str(self.IntDevice.unitnum)).log()

    def abort(self,
              **kwargs):
        tel = self.IntDevice.tel
        tel.abort()
        self.IntDevice.update_status()
    
    def run(self, 
            ra : float = None,
            dec : float = None,
            **kwargs):
        tel = self.IntDevice.tel
        if tel.condition == 'idle':
            tel.slew_radec(ra = float(ra), dec = float(dec))
        else:
            self._log.warning(f'Telescope {self.IntDevice.unitnum} is busy! Action SlewRADec is not triggered')
            pass
        self.IntDevice.update_status()
        
#%%
if __name__ == '__main__':
    device = IntegratedDevice(unitnum = 3)
    s =SlewRADec(device)
    s.run(ra = 310, dec= 30)
    

# %%
