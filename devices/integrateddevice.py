#%%
from tcspy.configuration import mainConfig
from tcspy.devices.camera import mainCamera
from tcspy.devices.focuser import mainFocuser_Alpaca
from tcspy.devices.focuser import mainFocuser_pwi4
from tcspy.devices.filterwheel import mainFilterwheel
from tcspy.devices.observer import mainObserver
from tcspy.devices.weather import mainWeather
from tcspy.devices.safetymonitor import mainSafetyMonitor
from tcspy.utils.error import *
from tcspy.devices.telescope import mainTelescope_Alpaca
from tcspy.devices.telescope import mainTelescope_pwi4
#%%
class IntegratedDevice(mainConfig):
    
    def __init__(self,
                 unitnum : int):
        super().__init__(unitnum= unitnum)
        self.tel_type = self.config['TELESCOPE_DEVICETYPE'].lower()
        self.focus_type = self.config['FOCUSER_DEVICETYPE'].lower()
        self.name = '7DT%.2d' % self.unitnum
        self.camera = None
        self.telescope = None
        self.focuser = None
        self.filterwheel = None
        self.weather = None
        self.safetymonitor = None
        self.observer = self._get_observer()
        self._set_devices()

    def _set_devices(self):
        self.camera = self._get_camera()
        self.telescope = self._get_telescope()
        self.focuser = self._get_focuser()
        self.filterwheel = self._get_filterwheel()
        self.weather = self._get_weather()
        self.safetymonitor = self._get_safetymonitor()
    
    def update_status(self):
        self.camera.status = self.camera.get_status()
        self.telescope.status = self.telescope.get_status()
        self.focuser.status = self.focuser.get_status()
        self.filterwheel.status = self.filterwheel.get_status()
        self.weather.status = self.weather.get_status()
        self.safetymonitor.status = self.safetymonitor.get_status()
    
    @property
    def status(self):
        self.update_status()
        status = dict()
        status['camera'] = self.camera.status
        status['telescope'] = self.telescope.status
        status['focuser'] = self.focuser.status
        status['filterwheel'] = self.filterwheel.status
        status['weather'] = self.weather.status
        status['safetymonitor'] = self.safetymonitor.status
        status['observer'] = self.observer.status
        return status
    
    @property
    def devices(self):
        devices = dict()
        devices['camera'] = self.camera
        devices['telescope'] = self.telescope
        devices['focuser'] = self.focuser
        devices['filterwheel'] = self.filterwheel
        devices['weather'] = self.weather
        devices['safetymonitor'] = self.safetymonitor
        return devices
    
    def _get_camera(self):
        return mainCamera(unitnum= self.unitnum)

    def _get_telescope(self):
        if self.tel_type.lower() == 'alpaca':
            return mainTelescope_Alpaca(unitnum= self.unitnum)
        elif self.tel_type.lower() == 'pwi4':
            return mainTelescope_pwi4(unitnum= self.unitnum)
        else: 
            return TelTypeError(f'Telescope Type "{self.focus_type}" is not defined')

    def _get_focuser(self):
        if self.focus_type.lower() == 'alpaca':
            return mainFocuser_Alpaca(unitnum= self.unitnum)
        elif self.focus_type.lower() == 'pwi4':
            return mainFocuser_pwi4(unitnum= self.unitnum)
        else:
            return FocuserTypeError(f'Focuser Type "{self.focus_type}" is not defined')
    
    def _get_filterwheel(self):
        return mainFilterwheel(unitnum= self.unitnum)
    
    def _get_observer(self):
        return mainObserver(unitnum= self.unitnum)
    
    def _get_weather(self):
        return mainWeather(unitnum= self.unitnum)
    
    def _get_safetymonitor(self):
        return mainSafetyMonitor(unitnum = self.unitnum)
    



# %%
IntegratedDevice(21)
# %%
