#%%
from multiprocessing import Event
from multiprocessing import Manager

from tcspy.configuration import mainConfig
from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.error import *
from tcspy.utils.logger import mainLogger
from tcspy.action.level1 import SlewRADec
from tcspy.action.level1 import SlewAltAz
from tcspy.action.level1 import ChangeFocus
from tcspy.action.level1 import ChangeFilter
from tcspy.action.level1 import Exposure

from tcspy.utils.image import mainImage
from tcspy.utils.target import SingleTarget
from tcspy.action.level2 import AutoFocus
from tcspy.utils.exception import *
import numpy as np
#%%
class AutoFlat(Interface_Runnable, Interface_Abortable):
    def __init__(self, 
                 singletelescope : SingleTelescope,
                 abort_action : Event):
        self.telescope = singletelescope
        self.telescope_status = TelescopeStatus(self.telescope)
        self.abort_action = abort_action
        self.shared_memory_manager = Manager()
        self.shared_memory = self.shared_memory_manager.dict()
        self.shared_memory['succeeded'] = False
        self.shared_memory['status'] = dict()
        self._log = mainLogger(unitnum = self.telescope.unitnum, logger_name = __name__+str(self.telescope.unitnum)).log()
        self.is_running = False
    
    def run(self,
            count : int = 9,
            gain : int = 2750,
            binning : int = 1):
        
        self._log.info(f'[{type(self).__name__}] is triggered.')
        self.is_running = True
        # Check condition of the instruments for this Action
        status_filterwheel = self.telescope_status.filterwheel
        status_camera = self.telescope_status.camera
        status_telescope = self.telescope_status.mount
        trigger_abort_disconnected = False
        if status_camera.lower() == 'disconnected':
            trigger_abort_disconnected = True
            self._log.critical(f'Camera is disconnected. Action "{type(self).__name__}" is not triggered')
        if status_filterwheel.lower() == 'disconnected':
            trigger_abort_disconnected = True
            self._log.critical(f'Filterwheel is disconnected. Action "{type(self).__name__}" is not triggered')
        if status_telescope.lower() == 'disconnected':
            trigger_abort_disconnected = True
            self._log.critical(f'Telescope is disconnected. Action "{type(self).__name__}" is not triggered') 
        if trigger_abort_disconnected:
            raise ConnectionException(f'[{type(self).__name__}] is failed: devices are disconnected.')
        
        # Abort action when triggered
        if self.abort_action.is_set():
            self.abort()

        # Define actions required
        action_slew = SlewAltAz(singletelescope = self.telescope, abort_action= self.abort_action)
        action_changefocus = ChangeFocus(singletelescope = self.telescope, abort_action = self.abort_action)
        action_changefilter = ChangeFilter(singletelescope = self.telescope, abort_action = self.abort_action)
        action_exposure = Exposure(singletelescope = self.telescope, abort_action = self.abort_action)
        
        # Slewing
        try:
            result_slew = action_slew.run(alt = self.telescope.config['AUTOFLAT_ALTITUDE'], az = self.telescope.config['AUTOFLAT_AZIMUTH'], tracking = False)
        except ConnectionException:
            self._log.critical(f'[{type(self).__name__}] is failed: telescope is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: telescope is disconnected.')
        except AbortionException:
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
        except ActionFailedException:
            self._log.critical(f'[{type(self).__name__}] is failed: slewing failure.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: slewing failure.')
        
        # Abort action when triggered
        if self.abort_action.is_set():
            self.abort()
          
        # Defocusing 
        try:
            result_changefocus = action_changefocus.run(position = 3000, is_relative= True)
        except ConnectionException:
            self._log.critical(f'[{type(self).__name__}] is failed: Focuser is disconnected.')                
            raise ConnectionException(f'[{type(self).__name__}] is failed: Focuser is disconnected.')                
        except AbortionException:
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
        except ActionFailedException:
            self._log.critical(f'[{type(self).__name__}] is failed: Focuser movement failure.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: Focuser movement failure.')
    
        # Abort action when triggered
        if self.abort_action.is_set():
            self.abort()
        
        # Get bias value
        camera = self.telescope.camera
        status_camera = self.telescope_status.camera
        # Check camera status
        if status_camera.lower() == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: camera is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: camera is disconnected.')
        elif status_camera.lower() == 'busy':
            self._log.critical(f'[{type(self).__name__}] is failed: camera is busy.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: camera is busy.')
        elif status_camera.lower() == 'idle':
            is_light = False
            self._log.info(f'Start exposure for calculation of a BIAS level')
            try:
                imginfo = camera.exposure(exptime = 0,
                                          imgtype = 'BIAS',
                                          binning = binning,
                                          is_light = is_light,
                                          gain = gain,
                                          abort_action = self.abort_action)
                bias_level = int(np.mean(imginfo['data']))
                self._log.info(f'BIAS level: {bias_level}')
            except ExposureFailedException:
                self.abort()
                self._log.critical(f'[{type(self).__name__}] is failed: camera exposure failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: camera exposure failure.')
            except AbortionException:
                self.abort()
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
            except:
                self.abort()
                self._log.warning(f'[{type(self).__name__}] is failed.')
                raise AbortionException(f'[{type(self).__name__}] is failed: BIAS level calculation failure')
        else:
            self._log.critical(f'[{type(self).__name__}] is failed: camera is under unknown condition.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: camera is under unknown condition.')

        filtnames = self.telescope.filterwheel.filtnames
        auto_flat_order = self.telescope.config.get('AUTOFLAT_FILTERORDER', [])
        defined_filtnames = [f for f in filtnames if f in auto_flat_order]
        ordered_filtnames = sorted(defined_filtnames, key=lambda x: auto_flat_order.index(x))
        observation_status = {filter_name: False for filter_name in ordered_filtnames}
        self.shared_memory['status'] = observation_status

        # Start autoflat
        def autoflat_filter(filter_, count, gain, binning):
            
            # Filterchange
            try:    
                result_filterchange = action_changefilter.run(filter_ = filter_)
            except ConnectionException:
                self._log.critical(f'[{type(self).__name__}] is failed: Filterwheel is disconnected.')                
                raise ConnectionException(f'[{type(self).__name__}] is failed: Filterwheel is disconnected.')                
            except AbortionException:
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
            except ActionFailedException:
                self._log.critical(f'[{type(self).__name__}] is failed: Filterwheel movement failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: Filterwheel movement failure.')
            
            # Exposure with default value & wait for the sky level arised
            obs_count = 0
            exptime = self.telescope.config['AUTOFLAT_MINEXPTIME']
            
            while obs_count < count:    
                # Check camera status
                status_camera = self.telescope_status.camera
                if status_camera.lower() == 'disconnected':
                    self._log.critical(f'[{type(self).__name__}] is failed: camera is disconnected.')
                    raise ConnectionException(f'[{type(self).__name__}] is failed: camera is disconnected.')
                elif status_camera.lower() == 'busy':
                    self._log.critical(f'[{type(self).__name__}] is failed: camera is busy.')
                    raise ActionFailedException(f'[{type(self).__name__}] is failed: camera is busy.')
                elif status_camera.lower() == 'idle':
                    self._log.info(f'Start exposure for calculation of a sky level')
                    try:
                        imginfo = camera.exposure(exptime = exptime,
                                                  imgtype = 'FLAT',
                                                  binning = binning,
                                                  is_light = True,
                                                  gain = gain,
                                                  abort_action = self.abort_action)
                        sky_level = int(np.mean(imginfo['data']) ) - bias_level + (30000*exptime + np.random.randint(0, 15000))
                        sky_level_per_second = sky_level/exptime
                        self._log.info(f'Sky level: {sky_level}')
                    except ExposureFailedException:
                        self.abort()
                        self._log.critical(f'[{type(self).__name__}] is failed: camera exposure failure.')
                        raise ActionFailedException(f'[{type(self).__name__}] is failed: camera exposure failure.')
                    except AbortionException:
                        self.abort()
                        self._log.warning(f'[{type(self).__name__}] is aborted.')
                        raise AbortionException(f'[{type(self).__name__}] is aborted.')
                    except:
                        self.abort()
                        self._log.warning(f'[{type(self).__name__}] is failed.')
                        raise AbortionException(f'[{type(self).__name__}] is failed: Sky level calculation failure')
                else:
                    self._log.critical(f'[{type(self).__name__}] is failed: camera is under unknown condition.')
                    raise ActionFailedException(f'[{type(self).__name__}] is failed: camera is under unknown condition.')
                
                # If sky level is within the range, then save the image
                if (sky_level > self.telescope.config['AUTOFLAT_MINCOUNT']) and (sky_level < self.telescope.config['AUTOFLAT_MAXCOUNT']):
                    target = SingleTarget(observer = self.telescope.observer, 
                                          ra = None,
                                          dec = None,
                                          alt = self.telescope.config['AUTOFLAT_ALTITUDE'], 
                                          az = self.telescope.config['AUTOFLAT_AZIMUTH'], 
                                          name = 'FLAT', 
                                          objtype= 'FLAT',
                                          id_ = None,
                                          note = None,
                                        
                                          exptime = exptime,
                                          count = 1,
                                          filter_ = filter_,
                                          binning = binning, 
                                          gain = gain,
                                          obsmode = None,
                                          specmode = None,
                                          ntelescope = 1
                                          )
                    status = self.telescope.status
                    try:
                        img = mainImage(frame_number = int(obs_count),
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
                        self._log.info(f'Saved!: %s'%(filepath))
                        obs_count += 1

                    except:
                        self._log.critical(f'[{type(self).__name__}] is failed: mainImage save failure.')
                        raise ActionFailedException(f'[{type(self).__name__}] is failed: mainImage save failure.')
                
                # Abort action when triggered
                if self.abort_action.is_set():
                    self.abort()
                
                # Adjust the exposure time
                exptime_min = np.round(np.abs(self.telescope.config['AUTOFLAT_MINCOUNT']/sky_level_per_second),2)
                exptime_max = np.round(np.abs(self.telescope.config['AUTOFLAT_MAXCOUNT']/sky_level_per_second),2)
                self._log.info('Required exposure time: (%s~%s) sec'%(exptime_min, exptime_max))
                
                # If sky level is too low, then wait for the sky level arised
                if exptime_min > self.telescope.config['AUTOFLAT_MAXEXPTIME']:
                    time.sleep(self.telescope.config['AUTOFLAT_WAITDURATION'])
                    self._log.info(f'Waiting {self.telescope.config["AUTOFLAT_WAITDURATION"]}s for the sky level arised')
                # If sky level is too high, raise an exception
                elif exptime_max < self.telescope.config['AUTOFLAT_MINEXPTIME']:
                    self._log.warning(f'[{type(self).__name__}] is failed: Sky is too bright.')
                    raise ActionFailedException(f'[{type(self).__name__}] is failed: Sky is too bright.')
                #
                else:
                    exptime = np.round(np.max([exptime_min, self.telescope.config['AUTOFLAT_MINEXPTIME']]),2)
                    self._log.info(f'Exposure time is adjusted to {exptime} sec')
            self._log.info(f'[{type(self).__name__}] for filter {filter_} is succeeded')
        
        for filtname in ordered_filtnames:
            try:
                autoflat_filter(filtname, count, gain, binning)
                observation_status[filtname] = True
                self.shared_memory['status'] = observation_status
            except ActionFailedException:
                self.log.critical(f'[{type(self).__name__}] is failed: autoflat_filter failure.')
            except ConnectionException:
                self.log.critical(f'[{type(self).__name__}] is failed: devices are disconnected.')
                raise ConnectionException(f'[{type(self).__name__}] is failed: devices are disconnected.')
            except AbortionException:
                self.log.critical(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
        self.is_running = False
        self.shared_memory['succeeded'] = True

    def abort(self):
        self.abort_action.set()
        self.is_running = False
        self._log.warning(f'[{type(self).__name__}] is aborted.')
        raise AbortionException(f'[{type(self).__name__}] is aborted.')
        
# %%

A = AutoFlat(SingleTelescope(21), Event())
# %%
