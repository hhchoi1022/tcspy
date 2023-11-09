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
        self._tel_type = tel_type
        self.cam = None
        self.tel = None
        self.focus = None
        self.filt = None
        self.obs = None
        self.weat = None
        self.safe = None
        self._set_devices()

    def _set_devices(self):
        self.cam = self._get_cam()
        self.tel = self._get_tel(tel_type = self._tel_type)
        self.focus = self._get_focus()
        self.filt = self._get_filtwheel()
        self.obs = self._get_observer()
        self.weat = self._get_weather()
        self.safe = self._get_safetymonitor()
    
    def update_status(self):
        self.cam.status = self.cam.get_status()
        self.tel.status = self.tel.get_status()
        self.focus.status = self.focus.get_status()
        self.filt.status = self.filt.get_status()
        self.obs.status = self.obs.get_status()
        self.weat.status = self.weat.get_status()
        self.safe.status = self.safe.get_status()
    
    @property
    def status(self):
        self.update_status()
        status = dict()
        status['camera'] = self.cam.status
        status['telescope'] = self.tel.status
        status['focuser'] = self.focus.status
        status['filterwheel'] = self.filt.status
        status['observer'] = self.obs.status
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
        devices['observer'] = self.obs
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
    
    
# # %%
# unit1 = Integreated_device(unitnum = 4)
# unit2 = Integreated_device(unitnum = 5)
# #%%
# devices = dict()
# devices['unit1'] = unit1
# devices['unit2'] = unit2

# # %%
# from threading import Thread
# from queue import Queue
# def slew_altaz(q,
#                **kwargs
#                ):
#     params = q.get()
#     device = devices[f'unit{params["unitnum"]}']
#     device.tel.slew_altaz(alt = params['alt'], az = params['az'])    
# #%%
# def exposure(unitnum : int,
#              exptime : float,
#              binning : int = 1,
#              imgtypename : str = 'object',
#              **kwargs
#              ):
#     device = devices[f'unit{unitnum}']
#     q.get()
#     device.cam.take_light(exptime = exptime, binning = binning, imgtypename = imgtypename)
# #%%
# az = 270
# alt = 40
# exptime = 60
# binning = 1
# imgtypename = 'object'
# #%%
# unitnums = [1,2]
# q = Queue()

# for unitnum in unitnums:
#     thread = Thread(target=slew_altaz, kwargs = {'q':q})
#     thread.start()
#     params = dict(unitnum = unitnum, alt = 0, az = 270)
#     q.put(params)
#     print(q.task_done())
# #%%
# q = Queue()
# for unitnum in unitnums:
#     thread = Thread(target=slew_altaz, kwargs = {'q':q})
#     thread.start()
#     params = dict(unitnum = unitnum, alt = 40, az = 90)
#     q.put(params)
#     q.task_done()
# # %%

# %%
