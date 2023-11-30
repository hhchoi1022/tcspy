#%%
from threading import Event
from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from tcspy.interfaces import *
from tcspy.utils.target import mainTarget
from tcspy.utils.image import mainImage
from tcspy.utils.logger import mainLogger
from tcspy.action.level1.changefilter import ChangeFilter

class Exposure(Interface_Runnable, Interface_Abortable):
    
    def __init__(self, 
                 Integrated_device : IntegratedDevice,
                 abort_action : Event):
        self.IDevice = Integrated_device
        self.IDevice_status = DeviceStatus(self.IDevice)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.IDevice.unitnum, logger_name = __name__+str(self.IDevice.unitnum)).log()

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
        
        # Check condition of the instruments for this Action
        status_filterwheel = self.IDevice_status.filterwheel
        status_camera = self.IDevice_status.camera
        trigger_abort_disconnected = False
        if status_camera.lower() == 'disconnected':
            trigger_abort_disconnected = True
            self._log.critical(f'Camera is disconnected. Action "{type(self).__name__}" is not triggered') 
        if status_filterwheel.lower() == 'disconnected':
            trigger_abort_disconnected = True
            self._log.critical(f'Filterwheel is disconnected. Action "{type(self).__name__}" is not triggered')
        if trigger_abort_disconnected:
            return False
        # Done

        # Action
        if self.abort_action.is_set():
            self.abort()
            return False
        else:
            # Set target
            if not target:
                target = mainTarget(unitnum = self.IDevice.unitnum, observer = self.IDevice.observer, target_name = target_name)
            
            # Move filter
            result_changefilter = True
            if imgtype.upper() == 'LIGHT':
                if status_filterwheel.lower() == 'idle':
                    changefilter = ChangeFilter(Integrated_device = self.IDevice, abort_action = self.abort_action)
                else:
                    self._log.critical(f'Filterwheel is busy. Action "{type(self).__name__}" is not triggered')
                    return False
                if not filter_:
                    self._log.critical('Filter must be determined for LIGHT frame')
                    return False
                result_changefilter = changefilter.run(str(filter_))
            
            # Check the filterchange succeeds or not
            if not result_changefilter:
                self._log.critical('Filterchange failed')
                return False
            
            # Exposure 
            if self.abort_action.is_set():
                self.abort()
                return False
            else:
                cam = self.IDevice.camera
                status_camera = self.IDevice_status.camera
                if status_camera.lower() == 'disconnected':
                    self._log.critical(f'Camera is disconnected. Action "{type(self).__name__}" is not triggered')
                    return False
                elif status_camera.lower() == 'idle':
                    
                    # Exposure camera
                    if imgtype.upper() == 'BIAS':
                        exptime = cam.device.ExposureMin
                        self._log.warning('Input exposure time is set to the minimum value for BIAS image')
                        is_light = False
                    if imgtype.upper() == 'DARK':
                        exptime = exptime
                        is_light = False
                    if imgtype.upper() == 'FLAT':
                        exptime = exptime
                        is_light = True
                    if imgtype.upper() in 'LIGHT':
                        exptime = exptime
                        is_light = True
                    self._log.info(f'[%s] Start exposure... (exptime = %.1f, filter = %s, binning = %s)'%(imgtype.upper(), exptime, filter_, binning))
                    imginfo = cam.exposure(exptime = float(exptime),
                                           imgtype = imgtype,
                                           binning = int(binning),
                                           is_light = is_light,
                                           abort_action = self.abort_action)
                    if self.abort_action.is_set():
                        self._log.warning(f'[{type(self).__name__}] is aborted.')
                        return False
                    else:
                        self._log.info(f'[%s] Exposure finished (exptime = %.1f, filter = %s, binning = %s)'%(imgtype.upper(), exptime, filter_, binning))
                        
                        # Save image
                        status = self.IDevice.status
                        img = mainImage(frame_number = int(frame_number),
                                        config_info = self.IDevice.config,
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
                        
                elif status_camera.lower() == 'busy':
                    self._log.critical(f'Camera is busy. Action "{type(self).__name__}" is not triggered')
                    return False
        return True

    def abort(self):
        status_filterwheel = self.IDevice_status.filterwheel
        status_camera = self.IDevice_status.camera
        if status_filterwheel.lower() == 'busy':
            self.IDevice.filterwheel.abort()
        if status_camera.lower() == 'busy':
            self.IDevice.camera.abort()
        
        
# %%

if __name__ == '__main__':
    device = IntegratedDevice(unitnum = 1)
    abort_action = Event()
    #device.filt.connect()
    #device.cam.connect()
    e =Exposure(device, abort_action)
    e.run(1, exptime = 1, filter_ = 'g')
# %%
