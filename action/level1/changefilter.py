#%%
from threading import Event

from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.exception import *

class ChangeFilter(Interface_Runnable, Interface_Abortable):
    
    def __init__(self, 
                 Integrated_device : IntegratedDevice,
                 abort_action : Event):
        self.IDevice = Integrated_device
        self.IDevice_status = DeviceStatus(self.IDevice)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.IDevice.unitnum, logger_name = __name__+str(self.IDevice.unitnum)).log()

    def run(self,
            filter_ : str):
        self._log.info(f'[{type(self).__name__}] is triggered.')
        # Check device connection
        if self.IDevice_status.filterwheel.lower() == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: filterwheel is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: filterwheel is disconnected.')
        
        # If not aborted, execute the action
        if self.abort_action.is_set():
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
        
        # Start action
        if self.IDevice_status.filterwheel.lower() == 'idle':
            try:
                result_move = self.IDevice.filterwheel.move(filter_ = filter_)
            except FilterChangeFailedException:
                self._log.critical(f'[{type(self).__name__}] is failed: filterwheel move failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: filterwheel move failure.')
                
        elif self.IDevice_status.filterwheel.lower() == 'busy':
            self._log.critical(f'[{type(self).__name__}] is failed: filterwheel is busy.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: filterwheel is busy.')
        else:
            self._log.critical(f'[{type(self).__name__}] is failed: filterwheel status error.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: filterwheel status error.')

        if result_move:
            self._log.info(f'[{type(self).__name__}] is finished.')
            return True
    
    def abort(self):
        return
