#%%
from tcspy.interfaces import *
from tcspy.devices import IntegratedDevice
import time
from tcspy.devices import DeviceStatus
from tcspy.utils.logger import mainLogger
#%%
class Connect(Interface_Runnable):
    
    def __init__(self, 
                 Integrated_device : IntegratedDevice):
        self.IDevice = Integrated_device
        self.Idevice_status = DeviceStatus(self.IDevice)
        self._log = mainLogger(unitnum = self.IDevice.unitnum, logger_name = __name__+str(self.IDevice.unitnum)).log()
    
    def run(self,
            **kwargs):
        
        # connect devices
        self._log.info(f'Action "{type(self).__name__}" starts')
        devices_status = self.Idevice_status.dict
        for device_name in self.IDevice.devices.keys():
            device = self.IDevice.devices[device_name]
            status = devices_status[device_name]
            try:
                if status == 'disconnected':
                    device.connect()
                else:
                    self._log.info(f'{device_name} connected')
                time.sleep(1)
            except:
                pass
        
        # check the device connection
        devices_status = self.Idevice_status.dict
        self._log.info('Checking devices connection...')
        for device_name in self.IDevice.devices.keys():
            device = self.IDevice.devices[device_name]
            status = devices_status[device_name]
            if status == 'disconnected':
                self._log.critical(f'{device_name} cannot be connected. Check the physical connection of the device')
            else:
                pass
            time.sleep(0.3)
        self._log.info(f'Action "{type(self).__name__}" finished.')
        time.sleep(1)      

# %%
if __name__ == '__main__':
    tel1 = IntegratedDevice(unitnum = 1)
    tel2 = IntegratedDevice(unitnum = 2)
    c1 = Connect(tel1)
    c2 = Connect(tel2)
    c1.run()
    c2.run()

#%%