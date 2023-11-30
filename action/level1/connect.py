#%%
import time
from threading import Event

from tcspy.devices import DeviceStatus
from tcspy.utils.logger import mainLogger
from tcspy.interfaces import *
from tcspy.devices import IntegratedDevice
#%%
class Connect(Interface_Runnable):
    
    def __init__(self, 
                 Integrated_device : IntegratedDevice,
                 abort_action : Event):
        self.IDevice = Integrated_device
        self.IDevice_status = DeviceStatus(self.IDevice)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.IDevice.unitnum, logger_name = __name__+str(self.IDevice.unitnum)).log()
    
    def run(self,
            **kwargs):
        
        # connect devices
        self._log.info(f'[{type(self).__name__}] is triggered.')
        devices_status = self.IDevice_status.dict
        for device_name in self.IDevice.devices.keys():
            if not self.abort_action.is_set():
                device = self.IDevice.devices[device_name]
                status = devices_status[device_name]
                try:
                    if status == 'disconnected':
                        device.connect()
                    else:
                        self._log.info(f'{device_name} is connected')
                    time.sleep(1)
                except:
                    pass
            else:
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                return
        
        # check the device connection
        devices_status = self.IDevice_status.dict
        self._log.info('Checking devices connection...')
        self._log.info('='*30)
        for device_name in self.IDevice.devices.keys():
            if not self.abort_action.is_set():
                device = self.IDevice.devices[device_name]
                status = devices_status[device_name]
                if status == 'disconnected':
                    self._log.critical(f'{device_name} cannot be connected. Check the physical connection of the device')
                else:
                    self._log.info(f'{device_name} : Connected')
            else:
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                return
            
        self._log.info('='*30)
        self._log.info(f'[{type(self).__name__}] is finished.')
        time.sleep(1)
    
    def abort(self):
        return
# %%
if __name__ == '__main__':
    tel1 = IntegratedDevice(unitnum = 1)
    tel2 = IntegratedDevice(unitnum = 2)
    c1 = Connect(tel1)
    c2 = Connect(tel2)
    c1.run()
    #c2.run()

#%%