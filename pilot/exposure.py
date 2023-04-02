#%%
from tcspy.utils.target import mainTarget
from tcspy.utils import DeviceInfo
from tcspy.utils.images import mainImage
def exposure(unitnum : int = 4,
             target_ra : float = None, # in hour
             target_dec : float = None,
             target_alt : float = None,
             target_az : float = None,
             target_name = '',
             exptime : float = None,
             counts : int = 1,
             filter_ : str = None,
             imgtype : str = 'light',
             binning : int = 1,
            **kwargs):
    devinfo = DeviceInfo(unitnum=unitnum)
    devices = devinfo.devices
    status = devinfo.status
    observer = devinfo.observer
    target = mainTarget(unitnum = unitnum, observer = observer, target_ra = target_ra, target_dec = target_dec, target_alt = target_alt, target_az = target_az, target_name = target_name )
        
    if not filter_ == None:
        devices['filterwheel'].move(filter_)
    for count in range(counts):
        if imgtype.upper() == 'LIGHT':
            img_status, cam_status = devices['camera'].take_light(exptime = exptime, binning = binning, imgtypename= imgtype)
        elif imgtype.upper() == 'DARK':
            img_status, cam_status = devices['camera'].take_dark(exptime = exptime, binning = binning, imgtypename= imgtype)
        elif imgtype.upper() == 'BIAS':
            img_status, cam_status = devices['camera'].take_bias(exptime = exptime, binning = binning, imgtypename= imgtype)
        status = devinfo.update_status()
        obs_status = observer.get_info()
        target_status = target.get_status()
        image = mainImage(unitnum = unitnum, image_info = img_status, camera_info = cam_status, telescope_info = status['telescope'], filterwheel_info = status['filterwheel'], focuser_info = status['focuser'], observer_info = obs_status, target_info = target_status)
    return image