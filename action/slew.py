

#%%
from tcspy.devices import IntegratedDevice
from tcspy.utils.target import mainTarget
from tcspy.devices.integrateddevice import IntegratedDevice
from tcspy.interfaces import *

class Slew(Interface_Slew):
    def __init__(self, 
                 Integrated_device : IntegratedDevice):
        self.IntDevice = Integrated_device
        
    def abort(self):
        tel = self.IntDevice.tel
        tel.abort()
        self.IntDevice.update_status()
    
    def slew_RADec(self, 
                   ra : float = None,
                   dec : float = None,
                   name : str = ''):
        tel = self.IntDevice.tel
        #target = mainTarget(unitnum = self.IntDevice.unitnum, observer = self.IntDevice.obs, target_ra = ra, target_dec = dec, target_name = name)
        #tel.slew_radec(ra = target.ra, dec = target.dec)
        tel.slew_radec(ra = ra, dec = dec)
        self.IntDevice.update_status()

    def slew_AltAz(self,
                   alt : float = None,
                   az : float = None,
                   name : str = ''):
        tel = self.IntDevice.tel   
        #target = mainTarget(unitnum = self.IntDevice.unitnum, observer = self.IntDevice.obs, target_alt = target_alt, target_az = target_az, target_name = target_name)
        #tel.slew_altaz(alt = target.alt, az = target.az)
        tel.slew_altaz(alt = alt, az = az)
        self.IntDevice.update_status()
        
#%%
if __name__ == '__main__':
    device = IntegratedDevice(unitnum = 1)
    s =Slew(device)
    s.slew_AltAz(alt=4, az= 270)    
    

# %%
