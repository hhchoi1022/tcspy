#%%
from tcspy.interfaces import *
from tcspy.devices import IntegratedDevice
import time

class Connect(Interface_Runnable):
    
    def __init__(self, 
                 Integrated_device : IntegratedDevice):
        self.IntDevice = Integrated_device
    
    def run(self,
            **kwargs):
        """connect to the device

        Args:
            device : device to be connected
        """
        
        for device_name in self.IntDevice.devices.keys():
            device = self.IntDevice.devices[device_name]
            try:
                device.connect()
                time.sleep(1)
            except:
                pass
        time.sleep(1)      
