#%%
from tcspy.interfaces import *
from tcspy.devices import IntegratedDevice
from tcspy.utils.target import mainTarget
from tcspy.utils.image import mainImage
from tcspy.utils.logger import mainLogger
from tcspy.action.level1.changefilter import ChangeFilter
from threading import Thread, Event

#%%
class Exposure(Interface_Runnable, Interface_Abortable):
    
    def __init__(self, 
                 Integrated_device : IntegratedDevice,
                 abort_action : Event):
        self.IntDevice = Integrated_device
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.IntDevice.unitnum, logger_name = __name__+str(self.IntDevice.unitnum)).log()

    def run(self,
            frame_number : int,
            exptime : float,
            filter_ : str = None,
            imgtype : str = 'Light',
            binning : int = 1,
            target_name : str = None,
            target : mainTarget = None):
        """_summary_

        Args:
            frame_number =1
            exptime =5
            filter_ ='g'
            imgtype = 'Light'
            binning =1
            target_name =None
            target = None

        Raises:
            ValueError: _description_
        """
        
        cam = self.IntDevice.cam
        changefilter = ChangeFilter(Integrated_device = self.IntDevice, abort_action = self.abort_action)
        
        if not self.abort_action.is_set():
            # Set target
            if not target:
                target = mainTarget(unitnum = self.IntDevice.unitnum, observer = self.IntDevice.obs, target_name = target_name)
            
            # Move filter
            if imgtype.upper() == 'LIGHT':
                if not filter_:
                    raise ValueError('filter must be defined')
                changefilter.run(str(filter_))
            
            # Set exposure config
            self._log.info(f'[%s] Start exposure... (exptime = %.1f, filter = %s, binning = %s)'%(imgtype.upper(), exptime, filter_, binning))
            imginfo = cam.exposure(exptime = float(exptime), imgtype = imgtype, binning = int(binning))
            self._log.info(f'[%s] Exposure finished (exptime = %.1f, filter = %s, binning = %s)'%(imgtype.upper(), exptime, filter_, binning))
            status = self.IntDevice.status
            
            img = mainImage(frame_number = int(frame_number),
                            config_info = self.IntDevice.config,
                            image_info = imginfo,
                            camera_info = status['camera'],
                            telescope_info = status['telescope'],
                            filterwheel_info = status['filterwheel'],
                            focuser_info = status['focuser'],
                            observer_info = status['observer'],
                            target_info = target.status,
                            weather_info = status['weather'])
            filepath = img.save()
            self._log.info(f'Saved!: %s)'%(filepath))
        else:
            self.abort()

    def abort(self):
        self.IntDevice.cam.abort()
        self.IntDevice.filt.abort()
        
# %%

if __name__ == '__main__':
    device = IntegratedDevice(unitnum = 1)
    device.filt.connect()
    device.cam.connect()
    e =Exposure(device)
    e.run(1, exptime = 1, filter_ = 'g')
# %%
