#%%
from tcspy.interfaces import *
from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from threading import Event
from tcspy.utils.logger import mainLogger
#%%

class Cool(Interface_Runnable, Interface_Abortable):
    
    def __init__(self, 
                 Integrated_device : IntegratedDevice,
                 abort_action : Event):
        self.IDevice = Integrated_device
        self.IDevice_status = DeviceStatus(self.IDevice)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.IDevice.unitnum, logger_name = __name__+str(self.IDevice.unitnum)).log()

    def run(self,
            settemperature : float,
            tolerance : float = 1):
        # Check device connection
        if self.IDevice_status.camera.lower() == 'disconnected':
            self._log.critical(f'Camera is disconnected. Action "{type(self).__name__}" is not triggered')
            return 
        
        # If not aborted, execute the action
        if not self.abort_action.is_set():
            self._log.info(f'[{type(self).__name__}] is triggered.')
            self.IDevice.cam.cool(settemperature = settemperature, 
                                  tolerance = tolerance)
            self._log.info(f'[{type(self).__name__}] is finished.')
        else:
            self.abort()
    
    def abort(self):
        # Raise critical warning when disconnected
        status_camera = self.IDevice_status.camera.lower()
        if status_camera == 'disconnected':
            self._log.critical(f'Camera is disconnected. Action "{type(self).__name__}" is not triggered')
            return 
        elif status_camera == 'busy':
            if self.Idevice.camera.device.CCDTemperature < self.Idevice.camera.device.CCDTemperature -20:
                self._log.critical(f'Turning off when the CCD Temperature below ambient may lead to damage to the sensor.')
                self.Idevice.camera.cooler_off()
            else:
                self.Idevice.camera.cooler_off()
        else:
            return
# %%
if __name__ == '__main__':
    tel1 = IntegratedDevice(unitnum = 1)
    tel2 = IntegratedDevice(unitnum = 2)
    abort_action = Event()
    Cool(tel1, abort_action).run(-20)


#%%