#%%
from tcspy.pilot import StartUp
from tcspy.devices.telescope import mainTelescope_Alpaca
from tcspy.devices.telescope import mainTelescope_pwi4
from tcspy.utils.target import mainTarget
from tcspy.devices.observer import mainObserver
from tcspy.utils import DeviceInfo
#%%
def slew(unitnum : int = 4,
         target_ra : float = None, # in hour
         target_dec : float = None,
         target_alt : float = None,
         target_az : float = None,
         **kwargs):
    devinfo = DeviceInfo(unitnum = unitnum)
    devices = devinfo.devices
    observer = devinfo.observer
    target = mainTarget(unitnum = unitnum, observer = observer, target_ra = target_ra, target_dec = target_dec, target_alt = target_alt, target_az = target_az)    
    
    if target.status['coordtype'] == 'radec':
        devices['telescope'].slew_radec(coordinate = target.coordinate)
    else:
        devices['telescope'].slew_altaz(coordinate= target.coordinate)
# %%
