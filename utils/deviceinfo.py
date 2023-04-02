
#%%
from tcspy.devices.telescope import mainTelescope_Alpaca
from tcspy.devices.telescope import mainTelescope_pwi4
from tcspy.devices.camera import mainCamera
from tcspy.devices.observer import mainObserver
from tcspy.devices.filterwheel import mainFilterwheel
from tcspy.devices.weather import mainWeather
from tcspy.devices.focuser import mainFocuser
from tcspy.configuration import mainConfig

class DeviceInfo(mainConfig):
    
    def __init__(self,
                 unitnum : int = 4):
        super().__init__(unitnum = unitnum)
        self._unitnum = unitnum
        self.devices = self._devices()
        self.status = self.update_status()
        self.observer = mainObserver(unitnum = unitnum)
    
    def _devices(self):
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
    
    def update_status(self):
        status_devices = dict()
        for name, device in self.devices.items():
            status = None
            if device != None:
                status = device.status
            status_devices[name] = status
        self.observer = mainObserver
        return status_devices
#%%
        