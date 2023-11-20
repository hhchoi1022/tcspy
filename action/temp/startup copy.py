#%%
from tcspy.devices import IntegratedDevice
from tcspy.utils.mainlogger import mainLogger
from tcspy.utils import LogFormat
from action.level1 import *

#%%
class StartUp:
    
    def __init__(self,
                 devices : IntegratedDevice,
                 CCD_temperature : int = -10,
                 **kwargs):
        self.log = mainLogger(unitnum = devices.unitnum, logger_name = __name__+str(devices.unitnum)).log()

        self.device = devices.devices
        self.status = devices.status
        self.temperature = CCD_temperature
    
    def connect(self):
        
    
    def run(self):
        self._log.info(LogFormat('StartUp').message_with_border(width = 70))
        self._log.info("Observer information setting compleated!\n==================\n   Observer = %s\n   Observatory = %s\n   Latitude = %s\n   Longitude = %s\n   Elevation = %s\n   Timezone = %s\n=================="%(self.observer._name, self.observer._observatory, self.observer._latitude, self.observer._longitude, self.observer._elevation, self.observer._timezone))
        self._log.info(LogFormat('Connecting devices').message_with_border(width = 50, border_char= '-'))
        self.connect_devices()
        self._log.info(LogFormat('Connection completed').message_with_border(width = 50, border_char= '-'))
        
        time.sleep(3)
        self._log.info(LogFormat('Checking device connection').message_with_border(width = 50, border_char= '-'))
        condition_key, devices = self.check_devices()
        self._log.info(LogFormat('Checking device completed').message_with_border(width = 50, border_char= '-'))
        if condition_key:
            tel = devices['telescope']
            cam = devices['camera']
            tel.park()
            tel.unpark()
            cam.cooler_on(sensortemperature)
            self._log.info(LogFormat('Startup Completed').message_with_border(width = 70))
            return devices
        else:
            self._log.critical(LogFormat('Startup process failed').message_with_border(width = 70))
            raise RuntimeError('======== Startup process failed ========')

        
        
        
        
                
        
        
# %%
if __name__ == '__main__':
    A = StartUp(unitnum = 5)
    connected_devices = A.run()
#%%

'''
# %%
tel, cam, focus, filt = A.devices
# %%
from astropy.coordinates import SkyCoord
target_coord = SkyCoord(ra = 15.2, dec = -40.64, unit = 'deg')
target_name = 'NGC1566'
#%%
tel.unpark()
#%%
tel.slew_target(ra = 125.5, dec = -70.64, target_name = 'NGC1566')

tel.slew_altaz(alt = 76.2, az = 55.5)
# %%
filt.move('w450')
# %%
focus.move(13500)
#%%
cam.take_light(exptime = 10, binning = 2)
# %%
'''