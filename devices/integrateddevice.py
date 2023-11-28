#%%
from tcspy.configuration import mainConfig
from tcspy.devices.camera import mainCamera
from tcspy.devices.telescope import mainTelescope_Alpaca
from tcspy.devices.telescope import mainTelescope_pwi4
from tcspy.devices.focuser import mainFocuser
from tcspy.devices.filterwheel import mainFilterwheel
from tcspy.devices.observer import mainObserver
from tcspy.devices.weather import mainWeather
from tcspy.devices.safetymonitor import mainSafetyMonitor

class IntegratedDevice(mainConfig):
    
    def __init__(self,
                 unitnum : int,
                 tel_type : str = 'Alpaca'):
        super().__init__(unitnum= unitnum)
        self.tel_type = tel_type
        self.cam = None
        self.tel = None
        self.focus = None
        self.filt = None
        self.weat = None
        self.safe = None
        self.observer = self._get_observer()
        self._set_devices()

    def _set_devices(self):
        self.cam = self._get_cam()
        self.tel = self._get_tel(tel_type = self.tel_type)
        self.focus = self._get_focus()
        self.filt = self._get_filtwheel()
        self.weat = self._get_weather()
        self.safe = self._get_safetymonitor()
    
    def update_status(self):
        self.cam.status = self.cam.get_status()
        self.tel.status = self.tel.get_status()
        self.focus.status = self.focus.get_status()
        self.filt.status = self.filt.get_status()
        self.weat.status = self.weat.get_status()
        self.safe.status = self.safe.get_status()
    
    
    @property
    def condition(self):
        condition = dict()
        condition['camera'] = self.cam.condition
        condition['telescope'] = self.tel.condition
        condition['focuser'] = self.focus.condition
        condition['filterwheel'] = self.filt.condition
        condition['weather'] = self.weat.condition
        condition['safetymonitor'] = self.safe.condition
        return condition

    @property
    def status(self):
        self.update_status()
        status = dict()
        status['camera'] = self.cam.status
        status['telescope'] = self.tel.status
        status['focuser'] = self.focus.status
        status['filterwheel'] = self.filt.status
        status['weather'] = self.weat.status
        status['safetymonitor'] = self.safe.status
        return status
    
    @property
    def devices(self):
        devices = dict()
        devices['camera'] = self.cam
        devices['telescope'] = self.tel
        devices['focuser'] = self.focus
        devices['filterwheel'] = self.filt
        devices['weather'] = self.weat
        devices['safetymonitor'] = self.safe
        return devices
    
    def _get_cam(self):
        return mainCamera(unitnum= self.unitnum)

    def _get_tel(self,
                 tel_type : str = 'Alpaca'):
        if tel_type.upper() == 'ALPACA':
            return mainTelescope_Alpaca(unitnum= self.unitnum)
        else:
            return mainTelescope_pwi4(unitnum= self.unitnum)

    def _get_focus(self):
        return mainFocuser(unitnum= self.unitnum)
    
    def _get_filtwheel(self):
        return mainFilterwheel(unitnum= self.unitnum)
    
    def _get_observer(self):
        return mainObserver(unitnum= self.unitnum)
    
    def _get_weather(self):
        return mainWeather(unitnum= self.unitnum)
    
    def _get_safetymonitor(self):
        return mainSafetyMonitor(unitnum = self.unitnum)
    
