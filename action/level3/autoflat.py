#%%
from threading import Event

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.error import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.target import mainTarget
from tcspy.action.level1.slewRADec import SlewRADec
from tcspy.action.level1.slewAltAz import SlewAltAz
from tcspy.action.level1.changefocus import ChangeFocus
from tcspy.action.level1.changefilter import ChangeFilter

from tcspy.action.level1.exposure import Exposure
from tcspy.action.level2.autofocus import Autofocus
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
        self._log = mainLogger(unitnum = self.telescope.unitnum, logger_name = __name__+str(self.telescope.unitnum)).log()
    
    def run(self,
            gain = 2750,
            binning = 1):
        
        self.multitelescopes.log.info(f'[{type(self).__name__}] is triggered.')
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
        # Done
        
        # Abort action when triggered
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise  AbortionException(f'[{type(self).__name__}] is aborted.')

        # Define actions required
        action_slew = SlewAltAz(singletelescope = self.telescope, abort_action= self.abort_action)
        action_changefocus = ChangeFocus(singletelescope = self.telescope, abort_action = self.abort_action)
        action_changefilter = ChangeFilter(singletelescope = self.telescope, abort_action = self.abort_action)
        action_exposure = Exposure(singletelescope = self.telescope, abort_action = self.abort_action)
        
        # Slewing
        try:
            result_slew = action_slew.run(alt = self.config['AUTOFLAT_ALT'], az = self.config['AUTOFLAT_AZ'], tracking = False)
        except ConnectionException:
            self._log.critical(f'[{type(self).__name__}] is failed: telescope is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: telescope is disconnected.')
        except AbortionException:
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
        except ActionFailedException:
            self._log.critical(f'[{type(self).__name__}] is failed: slewing failure.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: slewing failure.')

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
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise  AbortionException(f'[{type(self).__name__}] is aborted.')
        
        # Get bias value
        camera = self.telescope.camera
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

        

        
        
        exposure = Exposure(singletelescope = self.telescope, abort_action = self.abort_action)
        result_all_exposure = []
        
        for frame_number in range(count):
            try:
                result_exposure = exposure.run(frame_number = frame_number,
                                               exptime = exptime,
                                               filter_ = filter_,
                                               imgtype = imgtype,
                                               binning = binning,
                                               target_name = target_name,
                                               target = target
                                               )
                result_all_exposure.append(result_exposure)
            except ConnectionException:
                self._log.critical(f'[{type(self).__name__}] is failed: camera is disconnected.')
                raise ConnectionException(f'[{type(self).__name__}] is failed: camera is disconnected.')
            except AbortionException:
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
            except ActionFailedException:
                self._log.critical(f'[{type(self).__name__}] is failed: exposure failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: exposure failure.')
        return all(result_all_exposure)
            
    def abort(self):
        status_filterwheel = self.telescope_status.filterwheel
        status_camera = self.telescope_status.camera
        status_telescope = self.telescope_status.mount
        if status_filterwheel.lower() == 'busy':
            self.telescope.filterwheel.abort()
        if status_camera.lower() == 'busy':
            self.telescope.camera.abort()
        if status_telescope.lower() == 'busy':
            self.telescope.mount.abort()
    