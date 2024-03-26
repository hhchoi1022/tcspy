#%%
from threading import Event

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.exception import *

class ChangeFocus(Interface_Runnable, Interface_Abortable):
    
    def __init__(self, 
                 singletelescope : SingleTelescope,
                 abort_action : Event):
        self.telescope = singletelescope
        self.telescope_status = TelescopeStatus(self.telescope)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.telescope.unitnum, logger_name = __name__+str(self.telescope.unitnum)).log()

    def run(self,
            position: int = None,
            is_relative : bool = False):
        self._log.info(f'[{type(self).__name__}] is triggered.')
        # Check device connection
        if self.telescope_status.focuser.lower() == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: focuser is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: focuser is disconnected.')
        
        # If not aborted, execute the action
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
         
        # Start action
        if self.telescope_status.focuser.lower() == 'idle':
            try:
                info_focuser = self.telescope.focuser.get_status()
                if is_relative:
                    position = info_focuser['position'] + position
                result_move = self.telescope.focuser.move(position = position, abort_action= self.abort_action)
            except FocusChangeFailedException:
                self._log.critical(f'[{type(self).__name__}] is failed: focuser move failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: focuser move failure.')            
            except AbortionException:
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
        elif self.telescope_status.focuser.lower() == 'busy':
            self._log.critical(f'[{type(self).__name__}] is failed: focuser is busy.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: focuser is busy.')
        else:
            self._log.critical(f'[{type(self).__name__}] is failed: focuser status error.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: focuser status error.')

        if result_move:
            self._log.info(f'[{type(self).__name__}] is finished.')
        return True
    
    def abort(self):
        status_focuser = self.telescope_status.focuser.lower()
        if status_focuser == 'busy':
            self.telescope.focuser.abort()
        else:
            pass 
