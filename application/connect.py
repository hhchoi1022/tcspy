
#%%
from tcspy.devices import IntegratedDevice
from tcspy.devices.integrateddevice import IntegratedDevice
import time

def Connect(devices : IntegratedDevice):
    integrated_device = devices.devices

    for device_name in integrated_device.keys():
        device = integrated_device[device_name]
        try:
            device.connect()
            time.sleep(1)
        except:
            pass
    time.sleep(1)      
    status = devices.status
    return status

#%%
# A = IntegratedDevice(unitnum=0)
# stat = Connect(A)
# %%
