#%%
#%%
from threading import Event

from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from tcspy.interfaces import *
from tcspy.utils.error import *
from tcspy.utils.exception import *
from tcspy.utils.logger import mainLogger

from tcspy.action.level1 import ChangeFocus
from tcspy.action.level1 import ChangeFilter

#%%

class AutoFocus(Interface_Runnable, Interface_Abortable):
    def __init__(self, 
                 Integrated_device : IntegratedDevice,
                 abort_action : Event):
        self.IDevice = Integrated_device
        self.IDevice_status = DeviceStatus(self.IDevice)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.IDevice.unitnum, logger_name = __name__+str(self.IDevice.unitnum)).log()
    
    def run(self,
            filter_ : str,
            use_offset : bool):
        self._log.info(f'[{type(self).__name__}] is triggered.')
        # Check device status
        status_camera = self.IDevice_status.camera
        status_focuser = self.IDevice_status.focuser
        status_telescope = self.IDevice_status.telescope
        status_filterwheel = self.IDevice_status.filterwheel
        trigger_abort_disconnected = False
        if status_camera.lower() == 'disconnected':
            trigger_abort_disconnected = True
            self._log.critical(f'Camera is disconnected. Action "{type(self).__name__}" is not triggered')
        if status_focuser.lower() == 'disconnected':
            trigger_abort_disconnected = True
            self._log.critical(f'Focuser is disconnected. Action "{type(self).__name__}" is not triggered')
        if status_telescope.lower() == 'disconnected':
            trigger_abort_disconnected = True
            self._log.critical(f'Telescope is disconnected. Action "{type(self).__name__}" is not triggered')
        if status_filterwheel.lower() == 'disconnected':
            trigger_abort_disconnected = True
            self._log.critical(f'Filterwheel is disconnected. Action "{type(self).__name__}" is not triggered')
        if trigger_abort_disconnected:
            raise ConnectionException(f'[{type(self).__name__}] is failed: devices are disconnected.')
        
        # Abort action when triggered
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise  AbortionException(f'[{type(self).__name__}] is aborted.')
        
        if use_offset:
            info_filterwheel = self.IDevice.filterwheel.get_status()
            current_filter = info_filterwheel['filter']
            if not current_filter == filter_:
                offset = self.IDevice.filterwheel.get_offset_from_currentfilt(filter_ = filter_)
                self._log.info(f'Focuser is moving with the offset of {offset}[{current_filter} >>> {filter_}]')
                try:
                    result_focus = ChangeFocus(Integrated_device = self.IDevice, abort_action = self.abort_action).run(position = offset, is_relative= True)
                except ConnectionException:
                    self._log.critical(f'[{type(self).__name__}] is failed: Focuser is disconnected.')                
                    raise ConnectionException(f'[{type(self).__name__}] is failed: Focuser is disconnected.')                
                except AbortionException:
                    self._log.warning(f'[{type(self).__name__}] is aborted.')
                    raise AbortionException(f'[{type(self).__name__}] is aborted.')
                except ActionFailedException:
                    self._log.critical(f'[{type(self).__name__}] is failed: Focuser movement failure.')
                    raise ActionFailedException(f'[{type(self).__name__}] is failed: Focuser movement failure.')
            
        # Change filter
        info_filterwheel = self.IDevice.filterwheel.get_status()
        current_filter = info_filterwheel['filter']
        if not current_filter == filter_:
            try:
                result_filterchange = ChangeFilter(Integrated_device = self.IDevice, abort_action = self.abort_action).run(filter_ = filter_)
            except ConnectionException:
                self._log.critical(f'[{type(self).__name__}] is failed: Filterwheel is disconnected.')                
                raise ConnectionException(f'[{type(self).__name__}] is failed: Filterwheel is disconnected.')                
            except AbortionException:
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
            except ActionFailedException:
                self._log.critical(f'[{type(self).__name__}] is failed: Filterwheel movement failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: Filterwheel movement failure.')
        
        # run Autofocus
        info_focuser = self.IDevice.focuser.get_status()
        self._log.info(f'Start autofocus [Central focus position: {info_focuser["position"]}, filter: {filter_}')
        try:
            result_autofocus = self.IDevice.focuser.autofocus_start(abort_action = self.abort_action)
        except AbortionException:
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
        except AutofocusFailedException:
            self._log.warning(f'[{type(self).__name__}] is failed: Autofocus process is failed')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: Autofocus process is failed')
        
        if result_autofocus:
            self._log.info(f'[{type(self).__name__}] is finished')
            return True
    
    def abort(self):
        info_focuser = self.IDevice.focuser.get_status()
        if info_focuser['is_autofousing']:
            self.IDevice.focuser.autofocus_stop()
        if info_focuser['is_moving']:
            self.IDevice.focuser.abort()
        return 

        
        
        

        
        
        
            
    

        

    
    
