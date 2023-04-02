#%%
from tcspy.utils.target import mainTarget
from tcspy.utils import DeviceInfo
from tcspy.utils.images import mainImage
import time
from astropy.time import Time
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
        start = time.time()
        if imgtype.upper() == 'LIGHT':
            img_status, cam_status = devices['camera'].take_light(exptime = exptime, binning = binning, imgtypename= imgtype)
        elif imgtype.upper() == 'DARK':
            img_status, cam_status = devices['camera'].take_dark(exptime = exptime, binning = binning, imgtypename= imgtype)
        elif imgtype.upper() == 'BIAS':
            img_status, cam_status = devices['camera'].take_bias(binning = binning, imgtypename= imgtype)
        time_taken = time.time() - start
        status = devinfo.update_status()
        obs_status = observer.get_info()
        target_status = target.get_status()
        
        image = mainImage(unitnum = unitnum, image_info = img_status, camera_info = cam_status, telescope_info = status['telescope'], filterwheel_info = status['filterwheel'], focuser_info = status['focuser'], observer_info = obs_status, target_info = target_status)
        image.save(filename = 'test.fits')#f'{Time.now().jd}')
        
        print(time_taken)
    return image, time_taken
# %%
if __name__ =='__main__':
    time_takenall = []
    for i in range(10):
        binning = 4
        img, time_taken = exposure(unitnum = 4, target_alt = 40, target_az = 270, target_name = 'AAA', binning = binning, imgtype='bias')
        time_takenall.append(time_taken)

    time_taken_bin4 = time_takenall

    import matplotlib.pyplot as plt
    import numpy as np
    plt.plot(time_taken_bin1, c='k', label = f'32.8MB (binning1, [{(32.8/(np.mean(time_taken_bin1)-np.mean(time_taken_bin4))).round(1)}MB/s])')
    plt.plot(time_taken_bin2, c='g', label = f'8.2MB (binning2, [{(8.2/np.mean(time_taken_bin2-np.mean(time_taken_bin4))).round(1)}MB/s])')
    plt.plot(time_taken_bin3, c='r', label = f'3.6MB (binning3)')# [{(3.6/np.mean(time_taken_bin3)).round(1)}MB/s])')
    plt.plot(time_taken_bin4, c='r', label = f'2.1MB (binning4)')#, [{(2.1/np.mean(time_taken_bin4)).round(1)}MB/s])')
    plt.legend()
# %%
