#%%
from tcspy.devices.camera import mainCamera
from tcspy.devices.telescope import mainTelescope_Alpaca
from tcspy.devices.telescope import mainTelescope_pwi4
from tcspy.devices.focuser import mainFocuser
from tcspy.devices.filterwheel import mainFilterwheel
from tcspy.devices.observer import mainObserver
from tcspy.devices.weather import mainWeather
from tcspy.configuration import mainConfig
from tcspy.utils import mainLogger
import time

#%%
class StartUp(mainConfig):
    
    def __init__(self,
                 unitnum : int,
                 **kwargs):
        
        super().__init__(unitnum = unitnum)
        self._unitnum = unitnum
        self._log = mainLogger(unitnum = unitnum, logger_name = __name__+str(unitnum)).log()
        self.observer = mainObserver(unitnum = unitnum)
        self.devices = self.get_devices()
        self.status = self.get_status(self.devices)

    def get_devices(self):
        devices = dict()
        # telescope
        if self.config['TELESCOPE_DEVICE'].upper() == 'ALPACA':
            telescope = mainTelescope_Alpaca(unitnum= self._unitnum)
            devices['telescope'] = telescope
        else:
            telescope = mainTelescope_pwi4(unitnum= self._unitnum)
            devices['telescope'] = telescope
        # camera
        camera = mainCamera(unitnum= self._unitnum)
        devices['camera'] = camera    

        # filterwheel
        filterwheel = mainFilterwheel(unitnum= self._unitnum)
        devices['filterwheel'] = filterwheel            

        # weather
        weather = mainWeather(unitnum= self._unitnum)
        devices['weather'] = weather                  

        # focuser
        focuser = mainFocuser(unitnum= self._unitnum)
        devices['focuser'] = focuser
        return devices
    
    def get_status(self, devices):
        status_devices = dict()
        for name, device in devices.items():
            status = None
            if device != None:
                status = device.status
            status_devices[name] = status
        return status_devices
            
    def connect_devices(self):
        status_devices = self.get_status(self.devices)
        for device_name in status_devices.keys():
            device = self.devices[device_name]
            try:
                device.connect()
                time.sleep(1)
            except:
                pass
        time.sleep(1)      
        self.status = self.get_status(self.devices)
    
    def check_devices(self):
        condition_key = True
        connected_devices = dict()
        devices = self.get_devices()
        status_devices = self.get_status(self.devices)
        for device_name in status_devices.keys():
            status = status_devices[device_name]
            device = self.devices[device_name]
            if status['is_connected'] == None:
                self._log.critical('[Not registered] %s'%device_name)
            else:
                device = devices[device_name]
                connect_key = status['is_connected']
                if connect_key:
                    self._log.info('[Connected] %s'%device_name)
                    connected_devices[device_name] = device
                else:
                    self._log.critical('[Not Connected] %s'%device_name)
        obs_connect_key = (self.observer != None)
        if obs_connect_key:
            self._log.info('[Connected] Observer')
            connected_devices['observer'] = self.observer
        else:
            self._log.critical('[Not Connected] Observer. Startup process stopped')
            condition_key = False
        if ('telescope' not in connected_devices.keys()) & ('camera' not in connected_devices.keys()):
            self._log.critical('Telescope & Camera must be connected. Startup process stopped')
            condition_key = False
        time.sleep(3)
        weather_status = status_devices['weather']
        weather_device = devices['weather']
        if weather_status['is_connected']:
            weather_status = weather_device.get_status()
            if weather_status['is_safe']:
                self._log.info('Weather condition is good')
            if not weather_status['is_safe']:
                self._log.critical('Weather condition is bad. Startup process stopped')
                condition_key = False
        else:
            self._log.warning('Weather device is not connected')     
        self.status = self.get_status(self.devices)
        return condition_key, devices

    def run(self,
            sensortemperature : int = -15):
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