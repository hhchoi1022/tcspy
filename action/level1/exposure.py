#%%
from threading import Event
from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from tcspy.interfaces import *
from tcspy.utils.target import SingleTarget
from tcspy.utils.image import mainImage
from tcspy.utils.logger import mainLogger
from tcspy.utils.exception import *
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
            # Exposure information
            frame_number : int,
            exptime : float,
            filter_ : str = None,
            imgtype : str = 'Light',
            binning : int = 1,
            obsmode = 'Single',
            gain = 0,
            
            # Target information            
            ra : float = None,
            dec : float = None,
            alt : float = None,
            az : float = None,
            target_name : str = '',
            objtype : str = None,
            ):
        
        """
        frame_number = 1
        exptime = 1
        filter_ : str = None
        imgtype : str = 'BIAS'
        binning : int = 1
        target_name : str = None
        objtype = None
        obsmode = 'Single'
        """
        
        # Check condition of the instruments for this Action
        self._log.info(f'[{type(self).__name__}] is triggered.')
        status_filterwheel = self.IDevice_status.filterwheel
        status_camera = self.IDevice_status.camera
        trigger_abort_disconnected = False
        if status_camera.lower() == 'disconnected':
            trigger_abort_disconnected = True
            self._log.critical(f'[{type(self).__name__}] is failed: camera is disconnected.')
        if status_filterwheel.lower() == 'disconnected':
            trigger_abort_disconnected = True
            self._log.critical(f'[{type(self).__name__}] is failed: filterwheel is disconnected.')
        if trigger_abort_disconnected:
            raise ConnectionException(f'[{type(self).__name__}] is failed: devices are disconnected.')
        # Done
        
        # Action
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
        
        # Set target
        target = SingleTarget(observer = self.IDevice.observer, 
                              ra = ra, 
                              dec = dec, 
                              alt = alt, 
                              az = az, 
                              name = target_name, 
                              objtype= objtype,
                              
                              exptime = exptime,
                              count = 1,
                              filter_ = filter_,
                              binning = binning, 
                              obsmode = obsmode,
                              )
        exposure_info = target.exposure_info
        
        # Move filter
        result_changefilter = True
        if imgtype.upper() == 'LIGHT':
            if not filter_:
                self._log.critical('Filter must be determined for LIGHT frame')
                raise ActionFailedException('Filter must be determined for LIGHT frame')
            changefilter = ChangeFilter(Integrated_device = self.IDevice, abort_action = self.abort_action)    
            try:
                result_changefilter = changefilter.run(str(filter_))
            except ConnectionException:
                self._log.critical(f'[{type(self).__name__}] is failed: filterwheel is disconnected.')
                raise ConnectionException(f'[{type(self).__name__}] is failed: filterwheel is disconnected.')
            except AbortionException:
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
            except ActionFailedException:
                self._log.critical(f'[{type(self).__name__}] is failed: filterchange failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: filterchange failure.')

        # Exposure 
        # Check whether the process is aborted
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
        
        # Check device connection
        camera = self.IDevice.camera
        status_camera = self.IDevice_status.camera
        
        if status_camera.lower() == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: camera is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: camera is disconnected.')
        elif status_camera.lower() == 'busy':
            self._log.critical(f'[{type(self).__name__}] is failed: camera is busy.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: camera is busy.')
        elif status_camera.lower() == 'idle':
            # Exposure camera
            if imgtype.upper() == 'BIAS':
                exptime = camera.device.ExposureMin
                self._log.warning('Input exposure time is set to the minimum value for BIAS image')
                is_light = False
            elif imgtype.upper() == 'DARK':
                is_light = False
            elif imgtype.upper() == 'FLAT':
                is_light = True
            else:
                is_light = True
            self._log.info(f'[%s] Start exposure... (exptime = %.1f, filter = %s, binning = %s)'%(imgtype.upper(), exptime, filter_, binning))
            try:
                imginfo = camera.exposure(exptime = float(exptime),
                                          imgtype = imgtype,
                                          binning = int(binning),
                                          is_light = is_light,
                                          gain = gain,
                                          abort_action = self.abort_action)
                
            except ExposureFailedException:
                self.abort()
                self._log.critical(f'[{type(self).__name__}] is failed: camera exposure failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: camera exposure failure.')
            except AbortionException:
                self.abort()
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
            if imginfo:
                self._log.info(f'[%s] Exposure finished (exptime = %.1f, filter = %s, binning = %s)'%(imgtype.upper(), exptime, filter_, binning))
            
            # Save image
            if self.abort_action.is_set():
                self.abort()
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
            
            status = self.IDevice.status
            try:
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
                
            except:
                self._log.critical(f'[{type(self).__name__}] is failed: mainImage save failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: mainImage save failure.')
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
    device = IntegratedDevice(unitnum = 21)
    abort_action = Event()
    #device.filt.connect()
    #device.cam.connect()
    e =Exposure(device, abort_action)
    e.run(1, exptime = 1, filter_ = 'g', gain = 2750)
# %%
