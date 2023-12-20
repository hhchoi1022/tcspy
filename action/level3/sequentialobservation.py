#%%
from threading import Event
from astropy.table import Table

from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from tcspy.interfaces import *
from tcspy.utils.error import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.target import mainTarget
from tcspy.action.level1.slewRADec import SlewRADec
from tcspy.action.level1.slewAltAz import SlewAltAz
from tcspy.action.level1.exposure import Exposure
from tcspy.utils.exception import *
#%%
class SequentialObservation(Interface_Runnable, Interface_Abortable):
    def __init__(self, 
                 Integrated_device : IntegratedDevice,
                 abort_action : Event):
        self.IDevice = Integrated_device
        self.IDevice_status = DeviceStatus(self.IDevice)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.IDevice.unitnum, logger_name = __name__+str(self.IDevice.unitnum)).log()
    
    def run(self,
            target_tbl : Table,
            autofocus_when_init : bool,
            autofocus_when_filterchange : bool,
            autofocus_period : bool,
            use_focusoffset : bool 
            ):
        """ _Test_
        target_tbl = ascii.read('/home/hhchoi1022/tcspy/action/Daily_202312201403.csv')
        autofocus_when_init = True
        autofocus_when_filterchange = True
        autofocus_period = 60
        use_focusoffset = True

        """
        
        # Check condition of the instruments for this Action
        status_filterwheel = self.IDevice_status.filterwheel
        status_camera = self.IDevice_status.camera
        status_telescope = self.IDevice_status.telescope
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
            return ConnectionException(f'[{type(self).__name__}] is failed: devices are disconnected.')
        # Done
        
        # Slewing when not aborted
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            return  AbortionException(f'[{type(self).__name__}] is aborted.')
                
        # SingleObservation
        
        # Exposure when not aborted
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            return  AbortionException(f'[{type(self).__name__}] is aborted.')
        
        for target in target_tbl:
            filterwheel_status = self.IDevice.filterwheel.get_status()
            focus_status
            
            
        
    def abort(self):
        status_filterwheel = self.IDevice_status.filterwheel
        status_camera = self.IDevice_status.camera
        status_telescope = self.IDevice_status.telescope
        if status_filterwheel.lower() == 'busy':
            self.IDevice.filterwheel.abort()
        if status_camera.lower() == 'busy':
            self.IDevice.camera.abort()
        if status_telescope.lower() == 'busy':
            self.IDevice.telescope.abort()
    