#%%
from tcspy.devices import IntegratedDevice
from tcspy.devices.integrateddevice import IntegratedDevice
from utils.logger.mainlogger import mainLogger

#%%
def Check_connection(devices : IntegratedDevice):
    condition = True
    connected_devices = dict()
    integrated_device = devices.devices
    integrated_status = devices.status
    
    # Check connection
    for device_name in integrated_device.keys():
        device = integrated_device[device_name]
        status = integrated_status[device_name]
        connect_key = status['is_connected']
        
        if connect_key == None:
            if device_name.upper() in ['OBSERVER', 'TELESCOPE', 'CAMERA']:
                condition = False
        else:
            if connect_key:
                connected_devices[device_name] = device
            else:
                pass
    return condition


def Check_weather(devices : IntegratedDevice):
    # Check weather

    condition = True
    integrated_device = devices.devices
    integrated_status = devices.status
    weather_device = integrated_device['weather']
    weather_status = integrated_status['weather']
    
    if weather_status['is_connected']:
        weather_status = weather_device.get_status()
        if weather_status['is_safe']:
            pass
        if not weather_status['is_safe']:
            condition = False
    else:
        pass
    return condition

def Check_safetymonitor(devices : IntegratedDevice):
    # Check weather

    condition = True
    integrated_device = devices.devices
    integrated_status = devices.status
    weather_device = integrated_device['safetymonitor']
    weather_status = integrated_status['safetymonitor']
    
    if weather_status['is_connected']:
        weather_status = weather_device.get_status()
        if weather_status['is_safe']:
            pass
        if not weather_status['is_safe']:
            condition = False
    else:
        pass
    return condition

#%%
if __name__ == '__main__':
    device = IntegratedDevice(unitnum = 0)
    Check_safetymonitor(device)
    Check_connection(device)
    Check_weather(device)
# %%
