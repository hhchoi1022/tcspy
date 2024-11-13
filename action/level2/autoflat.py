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
import time
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
        self.is_focus_changed = False
    
    def run(self,
            count : int = 9,
            gain : int = 2750,
            binning : int = 1):
        
        self._log.info(f'==========LV2[{type(self).__name__}] is triggered.')
        if (self.telescope.safetymonitor.get_status()['is_safe'] == False) | (self.telescope.weather.get_status()['is_safe'] == False):
            self._log.warning(f'==========LV2[{type(self).__name__}] is failed: Unsafe weather.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: Unsafe weather.')
        self.is_running = True
        self.shared_memory['succeeded'] = False
        # Check condition of the instruments for this Action
        status_filterwheel = self.telescope_status.filterwheel
        status_camera = self.telescope_status.camera
        status_telescope = self.telescope_status.mount
        trigger_abort_disconnected = False
        if status_camera.lower() == 'disconnected':
            trigger_abort_disconnected = True
            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: camera is disconnected.')
        if status_filterwheel.lower() == 'disconnected':
            trigger_abort_disconnected = True
            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: filterwheel is disconnected.')
        if status_telescope.lower() == 'disconnected':
            trigger_abort_disconnected = True
            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: mount is disconnected.')
        if trigger_abort_disconnected:
            self.is_running = False
            raise ConnectionException(f'==========LV2[{type(self).__name__}] is failed: devices are disconnected.')
        
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
            self.is_running = False
            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: mount is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: mount is disconnected.')
        except AbortionException:
            self.abort()
        except ActionFailedException:
            self.is_running = False
            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: slewing failure.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: slewing failure.')
        
        # Abort action when triggered
        if self.abort_action.is_set():
            self.abort()
          
        # Defocusing 
        try:
            result_changefocus = action_changefocus.run(position = 3000, is_relative= True)
            self.is_focus_changed = True
        except ConnectionException:
            self.is_running = False
            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: Focuser is disconnected.')                
            raise ConnectionException(f'[{type(self).__name__}] is failed: Focuser is disconnected.')                
        except AbortionException:
            self.abort()
        except ActionFailedException:
            self.is_running = False
            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: Focuser movement failure.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: Focuser movement failure.')
    
        # Abort action when triggered
        if self.abort_action.is_set():
            self.abort()
        
        # Get bias value
        camera = self.telescope.camera
        status_camera = self.telescope_status.camera
        # Check camera status
        if status_camera.lower() == 'disconnected':
            self.is_running = False
            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: camera is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: camera is disconnected.')
        elif status_camera.lower() == 'busy':
            self.is_running = False
            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: camera is busy.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: camera is busy.')
        elif status_camera.lower() == 'idle':
            is_light = False
            self._log.info(f'=====[{type(self).__name__}] Start exposure for calculation of a BIAS level')
            try:
                imginfo = camera.exposure(exptime = 0,
                                          imgtype = 'BIAS',
                                          binning = binning,
                                          is_light = is_light,
                                          gain = gain,
                                          abort_action = self.abort_action)
                bias_level = float(np.mean(imginfo['data'])) 
                self._log.info(f'=====[{type(self).__name__}] BIAS level: {bias_level}')
            except ExposureFailedException:
                self.is_running = False
                self._log.critical(f'==========LV2[{type(self).__name__}] is failed: camera exposure failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: camera exposure failure.')
            except AbortionException:
                self.abort()
            except:
                self.is_running = False
                self._log.warning(f'==========LV2[{type(self).__name__}] is failed.')
                raise AbortionException(f'[{type(self).__name__}] is failed: BIAS level calculation failure')
        else:
            self.is_running = False
            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: camera is under unknown condition.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: camera is under unknown condition.')

        # Define the filter order for FLAT observation
        filtnames = self.telescope.filterwheel.filtnames
        auto_flat_order = self.telescope.config.get('AUTOFLAT_FILTERORDER', [])
        defined_filtnames = [f for f in filtnames if f in auto_flat_order]
        ordered_filtnames = sorted(defined_filtnames, key=lambda x: auto_flat_order.index(x))
        observation_status = {filter_name: False for filter_name in ordered_filtnames}
        self.shared_memory['status'] = observation_status

        # Start autoflat
        def autoflat_filter(filter_, count, gain, binning):
            self._log.info(f'=====[{type(self).__name__}] for filter {filter_} is triggered')
            # Filterchange
            try:    
                result_filterchange = action_changefilter.run(filter_ = filter_)
            except ConnectionException:
                self._log.critical(f'=====[{type(self).__name__}] is failed: Filterwheel is disconnected.')                
                raise ConnectionException(f'[{type(self).__name__}] is failed: Filterwheel is disconnected.')                
            except AbortionException:
                self._log.warning(f'=====[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
            except ActionFailedException:
                self._log.critical(f'=====[{type(self).__name__}] is failed: Filterwheel movement failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: Filterwheel movement failure.')
            
            # Exposure with default value & wait for the sky level arised
            obs_count = 0
            exptime = self.telescope.config['AUTOFLAT_MINEXPTIME']
            sky_level_per_second_this = 0
            
            while obs_count < count:    
                # Check camera status
                status_camera = self.telescope_status.camera
                if status_camera.lower() == 'disconnected':
                    self._log.critical(f'=====[{type(self).__name__}] is failed: camera is disconnected.')
                    raise ConnectionException(f'[{type(self).__name__}] is failed: camera is disconnected.')
                elif status_camera.lower() == 'busy':
                    self._log.critical(f'=====[{type(self).__name__}] is failed: camera is busy.')
                    raise ActionFailedException(f'[{type(self).__name__}] is failed: camera is busy.')
                elif status_camera.lower() == 'idle':
                    self._log.info(f'[{type(self).__name__}] Start exposure for calculation of a sky level')
                    try:
                        imginfo = camera.exposure(exptime = exptime,
                                                  imgtype = 'FLAT',
                                                  binning = binning,
                                                  is_light = True,
                                                  gain = gain,
                                                  abort_action = self.abort_action)
                        sky_level = float(np.mean(imginfo['data']) ) - bias_level
                        sky_level_acceleration = np.abs(sky_level_per_second_this - sky_level_per_second_this)
                        sky_level_per_second_this = sky_level/exptime 
                        sky_level_per_second_expected = sky_level_per_second_this + sky_level_acceleration
                        self._log.info(f'[{type(self).__name__}] Sky level: {sky_level} with {exptime}s exposure')
                    except ExposureFailedException:
                        self._log.critical(f'=====[{type(self).__name__}] is failed: camera exposure failure.')
                        raise ActionFailedException(f'[{type(self).__name__}] is failed: camera exposure failure.')
                    except AbortionException:
                        self._log.warning(f'=====[{type(self).__name__}] is aborted.')
                        raise AbortionException(f'[{type(self).__name__}] is aborted.')
                    except:
                        self._log.warning(f'=====[{type(self).__name__}] is failed.')
                        raise AbortionException(f'[{type(self).__name__}] is failed: Sky level calculation failure')
                else:
                    self._log.critical(f'=====[{type(self).__name__}] is failed: camera is under unknown condition.')
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
                                          is_ToO = False,
                                        
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
                        self._log.info(f'[{type(self).__name__}] Image saved: %s'%(filepath))
                        obs_count += 1

                    except:
                        self._log.critical(f'=====[{type(self).__name__}] is failed: mainImage save failure.')
                        raise ActionFailedException(f'[{type(self).__name__}] is failed: mainImage save failure.')
                
                # Abort action when triggered
                if self.abort_action.is_set():
                    self._log.warning(f'=====[{type(self).__name__}] is aborted.')
                    raise AbortionException(f'[{type(self).__name__}] is aborted.')
                
                # Adjust the exposure time
                exptime_min = np.round(np.abs(self.telescope.config['AUTOFLAT_MINCOUNT']/sky_level_per_second_expected),2)
                exptime_max = np.round(np.abs(self.telescope.config['AUTOFLAT_MAXCOUNT']/sky_level_per_second_this),2)
                self._log.info(f'[{type(self).__name__}] Required exposure time: (%s~%s) sec'%(exptime_min, exptime_max))
                
                # If sky level is too low, then wait for the sky level arised
                if exptime_min > self.telescope.config['AUTOFLAT_MAXEXPTIME']:
                    time.sleep(self.telescope.config['AUTOFLAT_WAITDURATION'])
                    self._log.info(f'[{type(self).__name__}] Waiting {self.telescope.config["AUTOFLAT_WAITDURATION"]}s for the sky level arised')
                # If sky level is too high, raise an exception
                elif exptime_max < self.telescope.config['AUTOFLAT_MINEXPTIME']:
                    self._log.warning(f'=====[{type(self).__name__}] is failed: Sky is too bright.')
                    raise ActionFailedException(f'[{type(self).__name__}] is failed: Sky is too bright.')
                #
                else:
                    exptime = np.round(np.max([np.sum([0.9*exptime_min, 0.1*exptime_max]), self.telescope.config['AUTOFLAT_MINEXPTIME']]),2)
                    self._log.info(f'[{type(self).__name__}] Exposure time is adjusted to {exptime} sec')
            self._log.info(f'=====[{type(self).__name__}] for filter {filter_} is succeeded')
        
        for filtname in ordered_filtnames:
            try:
                autoflat_filter(filtname, count, gain, binning)
                observation_status[filtname] = True
                self.shared_memory['status'] = observation_status
            except ActionFailedException:
                self.is_running = False
                self._log.critical(f'==========LV2[{type(self).__name__}] is failed: autoflat_filter failure.')
            except ConnectionException:
                self.is_running = False
                self._log.critical(f'==========LV2[{type(self).__name__}] is failed: devices are disconnected.')
                raise ConnectionException(f'[{type(self).__name__}] is failed: devices are disconnected.')
            except AbortionException:
                self.abort()
        
        # Defocusing 
        try:
            result_changefocus = action_changefocus.run(position = -3000, is_relative= True)
            self.is_focus_changed = False
        except ConnectionException:
            self.is_running = False
            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: Focuser is disconnected.')                
            raise ConnectionException(f'[{type(self).__name__}] is failed: Focuser is disconnected.')                
        except AbortionException:
            self.abort()
        except ActionFailedException:
            self.is_running = False
            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: Focuser movement failure.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: Focuser movement failure.')
    
        self.is_running = False
        self.shared_memory['succeeded'] = all(observation_status.values())
        
        self._log.info(f'==========LV2[{type(self).__name__}] is finished.')
        if self.shared_memory['succeeded']:
            return True    
        
    def abort(self):
        self.abort_action.set()
        time.sleep(10)
        # Defocusing 
        try:
            action_changefocus = ChangeFocus(singletelescope = self.telescope, abort_action = Event())
            result_changefocus = action_changefocus.run(position = -3000, is_relative= True)
        except ConnectionException:
            self.is_running = False
            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: Focuser is disconnected.')                
            raise ConnectionException(f'[{type(self).__name__}] is failed: Focuser is disconnected.')                
        except ActionFailedException:
            self.is_running = False
            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: Focuser movement failure.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: Focuser movement failure.')
    
        self.is_running = False
        self._log.warning(f'==========LV2[{type(self).__name__}] is aborted.')
        raise AbortionException(f'[{type(self).__name__}] is aborted.')
        

# %%
S = SingleTelescope(11)
# %%
B = AutoFlat(S, Event())
# %%
