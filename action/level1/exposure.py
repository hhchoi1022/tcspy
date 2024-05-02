#%%
from multiprocessing import Event
from multiprocessing import Manager

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.target import SingleTarget
from tcspy.utils.image import mainImage
from tcspy.utils.logger import mainLogger
from tcspy.utils.exception import *
from tcspy.action.level1.changefilter import ChangeFilter

class Exposure(Interface_Runnable, Interface_Abortable):

    def __init__(self, 
                 singletelescope : SingleTelescope,
                 abort_action : Event):
        self.telescope = singletelescope
        self.telescope_status = TelescopeStatus(self.telescope)
        self.abort_action = abort_action
        self.shared_memory_manager = Manager()
        self.shared_memory = self.shared_memory_manager.dict()
        self.shared_memory['succeeded'] = False
        self._log = mainLogger(unitnum = self.telescope.unitnum, logger_name = __name__+str(self.telescope.unitnum)).log()

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
            name : str = '',
            objtype : str = None,
            id_ : str = None
            ):
        """
        Performs the action to expose the camera, saves the image, and returns True if successful.

        Parameters
        ----------
        frame_number : int
            The number of the frame that is to be exposed.
        exptime : float
            The exposure time in seconds.
        filter_ : str, optional
            The filter that should be used during exposure.
        imgtype : str, optional
            The type of image to be taken. Defaults to 'Light'.
        binning : int, optional
            Binning factor for camera sensor. Defaults to 1.
        obsmode : str, optional
            The mode of observation. Defaults to 'Single'.
        gain : int, optional
            The gain setting for the camera sensor. Defaults to 0.
        ra, dec : float, optional
            Right Ascension and Declination, respectively, of the target in degrees.
        alt, az : float, optional
            Altitude and Azimuth, respectively, of the target in degrees
        name : str, optional
            Name of the target. 
        objtype : str, optional
            Type of the object targeted.


        Raises
        ------
        ConnectionException
            If the camera or the filterwheel is disconnected.
        ActionFailedException
            If there is an error during the change of filter or exposure.
        AbortionException
            If the operation is aborted.
        """
                
        """
        frame_number = 1
        exptime = 1
        filter_ : str = None
        imgtype : str = 'BIAS'
        binning : int = 1
        name : str = None
        objtype = None
        obsmode = 'Single'
        gain = 0
        ra : float = None
        dec : float = None
        alt : float = None
        az : float = None
        name : str = ''
        objtype : str = None
        """
        # Check condition of the instruments for this Action
        self._log.info(f'[{type(self).__name__}] is triggered.')
        status_filterwheel = self.telescope_status.filterwheel
        status_camera = self.telescope_status.camera
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
        target = SingleTarget(observer = self.telescope.observer, 
                              ra = ra, 
                              dec = dec, 
                              alt = alt, 
                              az = az, 
                              name = name, 
                              objtype= objtype,
                              id_ = id_,
                              
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
            info_filterwheel = self.telescope.filterwheel.get_status()
            current_filter = info_filterwheel['filter']
            is_filter_changed = (current_filter != filter_)
            if is_filter_changed:
                changefilter = ChangeFilter(singletelescope = self.telescope, abort_action = self.abort_action)    
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

        # Check device connection
        camera = self.telescope.camera
        status_camera = self.telescope_status.camera

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
            
            status = self.telescope.status
            try:
                img = mainImage(frame_number = int(frame_number),
                                config_info = self.telescope.config,
                                image_info = imginfo,
                                camera_info = status['camera'],
                                mount_info = status['mount'],
                                filterwheel_info = status['filterwheel'],
                                focuser_info = status['focuser'],
                                observer_info = status['observer'],
                                target_info = target.status,
                                weather_info = status['weather'])
                filepath = img.save()
                self._log.info(f'Saved!: %s)'%(filepath))
                self.shared_memory['succeeded'] = True
            except:
                self._log.critical(f'[{type(self).__name__}] is failed: mainImage save failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: mainImage save failure.')
        return True

    def abort(self):
        """
        Sends an abort command to the filterwheel and camera if they are busy.
        """
        self.abort_action.set()
        self.telescope.camera.abort()
        
        
# %%

if __name__ == '__main__':
    device = SingleTelescope(unitnum = 1)
    abort_action = Event()
    #device.filt.connect()
    #device.cam.connect()
    e =Exposure(device, abort_action)
    e.run(1, exptime = 1, filter_ = 'g', gain = 2750)
# %%
