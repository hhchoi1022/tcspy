#%%
from threading import Event

from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from tcspy.interfaces import *
from tcspy.utils.error import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.target import mainTarget
from tcspy.action.level1.slewRADec import SlewRADec
from tcspy.action.level1.slewAltAz import SlewAltAz
from tcspy.action.level1.exposure import Exposure
from tcspy.action.level2.autofocus import Autofocus
from tcspy.utils.exception import *
#%%
class SingleObservation(Interface_Runnable, Interface_Abortable):
    def __init__(self, 
                 Integrated_device : IntegratedDevice,
                 abort_action : Event):
        self.IDevice = Integrated_device
        self.IDevice_status = DeviceStatus(self.IDevice)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.IDevice.unitnum, logger_name = __name__+str(self.IDevice.unitnum)).log()
        
        
    
    def run(self, 
            exptime : float,
            count : int = 1,
            filter_ : str = None,
            imgtype : str = 'Light',
            binning : int = 1,
            ra : float = None,
            dec : float = None,
            alt : float = None,
            az : float = None,
            target_name : str = None,
            target_obsmode : str = 'Single',
            autofocus_before_start : bool = False
            ):
        
        
        
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
            raise ConnectionException(f'[{type(self).__name__}] is failed: devices are disconnected.')
        # Done
        
        # Slewing when not aborted
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise  AbortionException(f'[{type(self).__name__}] is aborted.')
        
        target = mainTarget(unitnum = self.IDevice.unitnum, observer = self.IDevice.observer, target_ra = ra, target_dec = dec, target_alt = alt, target_az = az, target_name = target_name, target_obsmode = target_obsmode)
         
        # Slewing
        if target.status['coordtype'] == 'radec':
            try:
                slew = SlewRADec(Integrated_device = self.IDevice, abort_action= self.abort_action)
                result_slew = slew.run(ra = target.status['ra'], dec = target.status['dec'])
            except ConnectionException:
                self._log.critical(f'[{type(self).__name__}] is failed: telescope is disconnected.')
                raise ConnectionException(f'[{type(self).__name__}] is failed: telescope is disconnected.')
            except AbortionException:
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
            except ActionFailedException:
                self._log.critical(f'[{type(self).__name__}] is failed: slewing failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: slewing failure.')

        elif target.status['coordtype'] == 'altaz':
            try:
                slew = SlewAltAz(Integrated_device = self.IDevice, abort_action= self.abort_action)
                result_slew = slew.run(alt = target.status['alt'], az = target.status['az'])
            except ConnectionException:
                self._log.critical(f'[{type(self).__name__}] is failed: telescope is disconnected.')
                raise ConnectionException(f'[{type(self).__name__}] is failed: telescope is disconnected.')
            except AbortionException:
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
            except ActionFailedException:
                self._log.critical(f'[{type(self).__name__}] is failed: slewing failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: slewing failure.')

        else:
            raise ActionFailedException(f'Coordinate type of the target : {target.status["coordtype"]} is not defined')
        
        # Autofocus when activated
        if autofocus_before_start:
            try:
                result_autofocus = Autofocus(Integrated_device= self.IDevice, abort_action= self.abort_action).run(filter_ = filter_).run()
            except ConnectionException:
                self._log.critical(f'[{type(self).__name__}] is failed: Device connection is lost.')
                raise ConnectionException(f'[{type(self).__name__}] is failed: Device connection is lost.')
            except AbortionException:
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
            except ActionFailedException:
                self._log.warning(f'[{type(self).__name__}] is failed: Autofocus is failed. Return to the previous focus value')
                pass
        
        # Exposure when not aborted
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise  AbortionException(f'[{type(self).__name__}] is aborted.')
        
        exposure = Exposure(Integrated_device = self.IDevice, abort_action = self.abort_action)
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
        status_filterwheel = self.IDevice_status.filterwheel
        status_camera = self.IDevice_status.camera
        status_telescope = self.IDevice_status.telescope
        if status_filterwheel.lower() == 'busy':
            self.IDevice.filterwheel.abort()
        if status_camera.lower() == 'busy':
            self.IDevice.camera.abort()
        if status_telescope.lower() == 'busy':
            self.IDevice.telescope.abort()
    