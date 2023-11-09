#%%
from tcspy.interfaces import *
from tcspy.devices import IntegratedDevice
from tcspy.utils.target import mainTarget
from tcspy.utils.image import mainImage

class Exposure(Interface_Exposure):
    
    def __init__(self, 
                 Integrated_device : IntegratedDevice):
        self.IntDevice = Integrated_device
    
    def exposure(self,
                 exptime : float,
                 filter_ : str = None,
                 imgtype : str = 'Light',
                 binning : int = 1,
                 target_name : str = None,
                 target : mainTarget = None):
        cam = self.IntDevice.cam
        filt = self.IntDevice.filt
        
        # Set target
        if not target:
            target = mainTarget(unitnum = self.IntDevice.unitnum, observer = self.IntDevice.obs, target_name = target_name)
        
        # Move filter
        if imgtype.upper() == 'LIGHT':
            if not filter_:
                raise ValueError('filter must be defined')
            filt.move(filter_)
        
        # Set exposure config
        imginfo = cam.exposure(exptime = exptime, imgtype = imgtype, binning = binning)
        
        status = self.IntDevice.status
        
        img = mainImage(config_info = self.IntDevice.config,
                        image_info = imginfo,
                        camera_info = status['camera'],
                        telescope_info = status['telescope'],
                        filterwheel_info = status['filterwheel'],
                        focuser_info = status['focuser'],
                        observer_info = status['observer'],
                        target_info = target.status)
        
        img.save(f'abc.fits')
        
        
    
    def abort(self):
        self.IntDevice.filt.abort()
#%%
device = IntegratedDevice(unitnum=1)
exp = Exposure(device)

#%%