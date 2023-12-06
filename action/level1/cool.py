#%%
from threading import Event

from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger

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
        self._log.info(f'[{type(self).__name__}] is triggered.')
        # Check device connection
        if self.IDevice_status.camera.lower() == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: camera is disconnected.')
            return False
        
        # If not aborted, execute the action
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            return False
        # Start action
        result_cool = self.IDevice.camera.cool(settemperature = settemperature, 
                                               tolerance = tolerance,
                                               abort_action = self.abort_action)
        if result_cool:
            self._log.info(f'[{type(self).__name__}] is finished.')
        else:
            self._log.critical(f'[{type(self).__name__}] is failed: camera cool failure.')
            return False
        return True
    
    def abort(self):
        if self.IDevice.camera.device.CoolerOn:
            if self.IDevice.camera.device.CCDTemperature < self.IDevice.camera.device.CCDTemperature -20:
                self._log.critical(f'Turning off when the CCD Temperature below ambient may lead to damage to the sensor.')
                self.IDevice.camera.cooler_off()
            else:
                self.IDevice.camera.cooler_off()
        else:
            pass
# %%
if __name__ == '__main__':
    tel1 = IntegratedDevice(unitnum = 21)
    tel2 = IntegratedDevice(unitnum = 22)
    #abort_action = Event()
    c = Cool(tel1, abort_action)


#%%