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

from alpaca import management
from alpaca import discovery
from alpaca.filterwheel import FilterWheel
from alpaca.focuser import Focuser
from alpaca.camera import Camera
from alpaca.telescope import Telescope
from alpaca.observingconditions import ObservingConditions
from tcspy.devices.telescope import PWI4

import time

#%%
log = mainLogger(__name__).log()
class StartUp(mainConfig):
    
    def __init__(self):
        
        super().__init__()
        self.observer = self.get_observer()
        self.devices = self.get_devices()
        self.status = self.get_status(self.devices)

    def get_observer(self):
        observer = mainObserver(**self.config)
        return observer
    
    def get_devices(self):
        def alpaca_format(host_ip, portnum):
            return host_ip + ':' + portnum
        camera = Camera(alpaca_format(self.config['CAMERA_HOSTIP'], self.config['CAMERA_PORTNUM']), self.config['CAMERA_DEVICENUM'])
        filterwheel = FilterWheel(alpaca_format(self.config['FTWHEEL_HOSTIP'], self.config['FTWHEEL_PORTNUM']), self.config['FTWHEEL_DEVICENUM'])
        focuser = Focuser(alpaca_format(self.config['FOCUSER_HOSTIP'], self.config['FOCUSER_PORTNUM']), self.config['FOCUSER_DEVICENUM'])
        weather = ObservingConditions(alpaca_format(self.config['WEATHER_HOSTIP'], self.config['WEATHER_PORTNUM']), self.config['WEATHER_DEVICENUM'])
        devices = dict()
        # telescope
        if self.config['TELESCOPE_DEVICE'].upper() == 'ALPACA':
            telescope = Telescope(alpaca_format(self.config['TELESCOPE_HOSTIP'], self.config['TELESCOPE_PORTNUM']), self.config['TELESCOPE_DEVICENUM'])
            dev_telescope = mainTelescope_Alpaca(telescope, observer = self.observer)
            devices['telescope'] = dev_telescope
        else:
            telescope = PWI4(self.config['TELESCOPE_HOSTIP'], self.config['TELESCOPE_PORTNUM'])
            dev_telescope = mainTelescope_pwi4(telescope, observer = self.observer)
            devices['telescope'] = dev_telescope
            
        # camera
        dev_camera = mainCamera(camera)
        devices['camera'] = dev_camera    

        # filterwheel
        dev_filterwheel = mainFilterwheel(filterwheel)
        devices['filterwheel'] = dev_filterwheel            

        # weather
        dev_weather = mainWeather(weather)
        devices['weather'] = dev_weather                  

        # focuser
        dev_focuser = mainFocuser(focuser)
        devices['focuser'] = dev_focuser
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
        log.info('======== Checking connection ========')
        connected_devices = dict()
        devices = self.get_devices()
        status_devices = self.get_status(self.devices)
        for device_name in status_devices.keys():
            status = status_devices[device_name]
            device = self.devices[device_name]
            if status['is_connected'] == None:
                log.critical('[Not registered] %s'%device_name)
            else:
                device = devices[device_name]
                connect_key = status['is_connected']
                if connect_key:
                    log.info('[Connected] %s'%device_name)
                    connected_devices[device_name] = device
                else:
                    log.critical('[Not Connected] %s'%device_name)
        obs_connect_key = (self.observer != None)
        if obs_connect_key:
            log.info('[Connected] Observer')
            connected_devices['observer'] = self.observer
        else:
            log.critical('[Not Connected] Observer. Startup process stopped')
            condition_key = False
        if ('telescope' not in connected_devices.keys()) & ('camera' not in connected_devices.keys()):
            log.critical('Telescope & Camera must be connected. Startup process stopped')
            condition_key = False
        log.info('======== Checking connection finished ========')
        time.sleep(3)
        log.info('======== Checking weather condition ========')
        weather_status = status_devices['weather']
        weather_device = devices['weather']
        if weather_status['is_connected']:
            weather_status = weather_device.get_status()
            if weather_status['is_safe']:
                log.info('Weather condition is good')
            if not weather_status['is_safe']:
                log.critical('Weather condition is bad. Startup process stopped')
                condition_key = False
        else:
            log.warning('Weather device is not connected')
        log.info('======== Checking weather finished ========')      
        self.status = self.get_status(self.devices)
        return condition_key, devices

    def run(self,
            sensortemperature : int = -15):
        self.connect_devices()
        time.sleep(3)
        condition_key, devices = self.check_devices()
        if condition_key:
            tel = devices['telescope']
            cam = devices['camera']
            tel.park()
            tel.unpark()
            cam.cooler_on(sensortemperature)
            log.info('======== Startup completed ========')
            return devices
        else:
            log.critical('Startup process failed')
            raise RuntimeError('======== Startup process failed ========')

        
        
        
        
                
        
        
# %%
if __name__ == '__main__':
    A = StartUp()
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