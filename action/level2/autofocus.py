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

#%%

class Autofocus(Interface_Runnable, Interface_Abortable):
    def __init__(self, 
                 Integrated_device : IntegratedDevice,
                 abort_action : Event):
        self.IDevice = Integrated_device
        self.IDevice_status = DeviceStatus(self.IDevice)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.IDevice.unitnum, logger_name = __name__+str(self.IDevice.unitnum)).log()
    
    def run(self,
            use_offset : bool = False):
        status_camera = self.IDevice_status.camera
        status_focuser = self.IDevice_status.focuser
        trigger_abort_disconnected = False
        if status_camera.lower() == 'disconnected':
            trigger_abort_disconnected = True
            self._log.critical(f'Camera is disconnected. Action "{type(self).__name__}" is not triggered')
        if status_focuser.lower() == 'disconnected':
            trigger_abort_disconnected = True
            self._log.critical(f'Focuser is disconnected. Action "{type(self).__name__}" is not triggered')
        if trigger_abort_disconnected:
            raise ConnectionException(f'[{type(self).__name__}] is failed: devices are disconnected.')
        # Done
        
        # Abort action when triggered
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise  AbortionException(f'[{type(self).__name__}] is aborted.')
        
        # When use_offset == True, move focusvalue based on the offset 
        if use_offset:
            ChangeFocus
    

        

    
    
