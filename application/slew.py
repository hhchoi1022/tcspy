

#%%
from tcspy.devices import IntegratedDevice
from tcspy.utils.target import mainTarget
from tcspy.devices.integrateddevice import IntegratedDevice

def Slew_RADec(devices : IntegratedDevice,
               target_ra : float = None,
               target_dec : float = None,
               target_name : str = ''):
    integrated_device = devices.devices
    integrated_status = devices.status
    
    device = integrated_device['telescope']
    status = integrated_status['telescope']
    
    target = mainTarget(unitnum = devices.unitnum, observer = integrated_device['observer'], target_ra = target_ra, target_dec = target_dec, target_name = target_name)
    device.slew_radec(ra = target.ra, dec = target.dec)
    status = devices.status
    return status

def Slew_AltAz(devices : IntegratedDevice,
               target_alt : float = None,
               target_az : float = None,
               target_name : str = ''):
    integrated_device = devices.devices
    target = mainTarget(unitnum = devices.unitnum, observer = integrated_device['observer'], target_alt = target_alt, target_az = target_az, target_name = target_name)
    device.tel.slew_altaz(alt = target.alt, az = target.az)
    status = devices.status
    return status
#%%
if __name__ == '__main__':
    device = IntegratedDevice(unitnum = 0)
    B = Slew_RADec(devices = device, target_ra = 30.244, target_dec = 50.232)
    C = Slew_AltAz(devices = device, target_alt = 32.9, target_az = 48.8)
