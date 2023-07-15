#%%
from tcspy.devices.camera import mainCamera
from tcspy.devices.telescope import mainTelescope_Alpaca
from tcspy.devices.telescope import mainTelescope_pwi4
from tcspy.devices.focuser import mainFocuser
from tcspy.devices.filterwheel import mainFilterwheel
from tcspy.devices.observer import mainObserver
from tcspy.devices.weather import mainWeather
from tcspy.devices.safetymonitor import mainSafetyMonitor
#%%


class Integreated_device:
    
    def __init__(self,
                 unitnum : int,
                 tel_type : str = 'Alpaca'):
        self.unitnum = unitnum
        self._tel_type = tel_type
        self.cam = None
        self.tel = None
        self.focus = None
        self.filt = None
        self.obs = None
        self.weat = None
        self.safe = None
        self.set_devices()

    def set_devices(self):
        self.cam = self._get_cam()
        self.tel = self._get_tel(tel_type = self._tel_type)
        self.focus = self._get_focus()
        self.filt = self._get_filtwheel()
        self.obs = self._get_observer()
        self.weat = self._get_weather()
        self.safe = self._get_safetymonitor()
        
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
    
    
# %%
unit1 = Integreated_device(unitnum = 1)
unit2 = Integreated_device(unitnum = 2)

# %%
