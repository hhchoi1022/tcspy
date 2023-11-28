#%%
from tcspy.interfaces import *
from tcspy.devices import IntegratedDevice
import time

class Disconnect(Interface_Runnable):
    
    def __init__(self, 
                 Integrated_device : IntegratedDevice):
        self.IntDevice = Integrated_device
    
    def run(self,
            **kwargs):
        for device_name in self.IntDevice.devices.keys():
            device = self.IntDevice.devices[device_name]
            try:
                device.disconnect()
                time.sleep(1)
            except:
                pass
        time.sleep(1)      

# %%
if __name__ == '__main__':
    tel1 = IntegratedDevice(unitnum = 1)
    tel2 = IntegratedDevice(unitnum = 2)
    Disconnect(tel1).run()
    Disconnect(tel2).run()
    

#%%