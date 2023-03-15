
#%%
from astropy.coordinates import SkyCoord
from typing import Optional

from tcspy.utils import to_SkyCoord
from tcspy.utils import mainLogger
from tcspy.configuration import mainConfig
from tcspy.devices.camera import mainCamera
from tcspy.devices.focuser import mainFocuser
from tcspy.devices.telescope import mainTelescope_pwi4
from tcspy.devices.telescope import mainTelescope_Alpaca
from tcspy.devices.filterwheel import mainFilterwheel
from tcspy.devices.observer import mainObserver
from tcspy.utils.target import mainTarget
from tcspy.utils.images import mainImage

#%%
class singleObservation(mainConfig):
    
    def __init__(self,
                 unitnum : int,
                 camera : mainCamera,
                 telescope : mainTelescope_pwi4 or mainTelescope_Alpaca,
                 observer : mainObserver,
                 filterwheel : mainFilterwheel,
                 focuser : mainFocuser,
                 **kwargs
                 ):
        super().__init__(unitnum = unitnum)
        self._unitnum = unitnum
        self._log = mainLogger(unitnum = unitnum, logger_name = __name__+str(unitnum)).log()
        self.tel = telescope
        self.cam = camera
        self.filt = filterwheel
        self.focus = focuser
        self.observer = observer
        
    def slew_exposure(self,
                      target_ra : float = None, # in hour
                      target_dec : float = None,
                      target_alt : float = None,
                      target_az : float = None,
                      target_name = '',
                      exptime : float = None,
                      counts : int = 1,
                      filter : str = None,
                      imgtype : str = 'light',
                      binning : int = 1):
        
        target = mainTarget(unitnum = self._unitnum, observer = self.observer, target_ra = target_ra, target_dec = target_dec, target_alt = target_alt, target_az = target_az, target_name = target_name )
        
        if target.status['coordtype'] == 'radec':
            self.tel.slew_radec(coordinate = target.coordinate)
        else:
            self.tel.slew_altaz(coordinate= target.coordinate)
        self.tel.status = self.tel.get_status()
            # move filter
        if not filter == None:
            self.filt.move(filter)
        
        for count in range(counts):
            if imgtype.upper() == 'LIGHT':
                img_status, cam_status = self.cam.take_light(exptime = exptime, binning = binning, imgtypename= imgtype)
            elif imgtype.upper() == 'DARK':
                img_status, cam_status = self.cam.take_dark(exptime = exptime, binning = binning, imgtypename= imgtype)
            elif imgtype.upper() == 'BIAS':
                img_status, cam_status = self.cam.take_bias(exptime = exptime, binning = binning, imgtypename= imgtype)
            tel_status = self.tel.get_status()
            filt_status = self.filt.get_status()
            focus_status = self.focus.get_status()
            obs_status = self.observer.get_info()
            target_status = target.get_status()
            image = mainImage(unitnum = self._unitnum, image_info = img_status, camera_info = cam_status, telescope_info = tel_status, filterwheel_info = filt_status, focuser_info = focus_status, observer_info = obs_status, target_info = target_status)
        return image
 #%% Test
if __name__ == '__main__':
    from tcspy.pilot import StartUp
    connected_devices = StartUp().run()
#%%
    
#%%
if __name__ == '__main__': 
    obs = singleObservation(**connected_devices)
    ra = '8:00:00'
    dec = '-49:09:04'
    coordinate_radec = to_SkyCoord(ra, dec)
    alt = 40
    az = 180
    hdu = obs.slew_exposure(target_ra = coordinate_radec.ra.hour, target_dec = coordinate_radec.dec.deg, exptime = 10, counts = 1, filter = 'w475', binning = 2)
    #stats = obs.slew_exposure(target_alt = alt, target_az = az, exptime = 10, counts = 1, filter = 'w475', binning = 2)
# %%
