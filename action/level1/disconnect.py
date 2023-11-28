#%%
from tcspy.interfaces import *
from tcspy.devices import IntegratedDevice
import time
from tcspy.devices import DeviceStatus
from tcspy.utils.logger import mainLogger
#%%
class Disconnect(Interface_Runnable):
    
    def __init__(self, 
                 Integrated_device : IntegratedDevice):
        self.IDevice = Integrated_device
        self.Idevice_status = DeviceStatus(self.IDevice)
        self._log = mainLogger(unitnum = self.IDevice.unitnum, logger_name = __name__+str(self.IDevice.unitnum)).log()
    
    def run(self,
            **kwargs):
        
        # disconnect devices
        self._log.info(f'Action "{type(self).__name__}" starts')
        devices_status = self.Idevice_status.dict
        for device_name in self.IDevice.devices.keys():
            device = self.IDevice.devices[device_name]
            status = devices_status[device_name]
            try:
                if not status == 'disconnected':
                    device.disconnect()
                else:
                    self._log.info(f'{device_name} disconnected')
                time.sleep(1)
            except:
                pass
        
        # check the device connection
        devices_status = self.Idevice_status.dict
        self._log.info('Checking devices connection...')
        for device_name in self.IDevice.devices.keys():
            device = self.IDevice.devices[device_name]
            status = devices_status[device_name]
            if not status == 'disconnected':
                self._log.critical(f'{device_name} cannot be disconnected. Check the ASCOM Remote Server')
            else:
                pass
            time.sleep(0.3)
        self._log.info(f'Action "{type(self).__name__}" finished.')
        time.sleep(1)      


# %%
if __name__ == '__main__':
    tel1 = IntegratedDevice(unitnum = 1)
    tel2 = IntegratedDevice(unitnum = 2)
    Disconnect(tel1).run()
    Disconnect(tel2).run()
    

#%%