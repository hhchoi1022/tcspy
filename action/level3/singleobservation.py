#%%
from threading import Event

from tcspy.devices import IntegratedDevice
from tcspy.utils.target import mainTarget
from tcspy.devices.integrateddevice import IntegratedDevice
from tcspy.interfaces import *
from tcspy.utils.error import *
from tcspy.action.level1.slewRADec import SlewRADec
from tcspy.action.level1.slewAltAz import SlewAltAz
from tcspy.action.level2.exposure import Exposure
from tcspy.utils.logger import mainLogger
from tcspy.devices import DeviceStatus
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
            target : mainTarget = None
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
            return
        # Done
        
        # Slewing when not aborted
        if not self.abort_action.is_set():
            if not target:
                target = mainTarget(unitnum = self.IDevice.unitnum, observer = self.IDevice.observer, target_ra = ra, target_dec = dec, target_alt = alt, target_az = az, target_name = target_name)
            
            if target.status['coordtype'] == None:
                pass
            
            elif target.status['coordtype'] == 'radec':
                slew = SlewRADec(Integrated_device = self.IDevice, abort_action= self.abort_action)
                slew.run(ra = target.status['ra'], dec = target.status['dec'])
            
            elif target.status['coordtype'] == 'altaz':
                slew = SlewAltAz(Integrated_device = self.IDevice, abort_action= self.abort_action)
                slew.run(alt = target.status['alt'], az = target.status['az'])
            
            else:
                raise ValueError(f'Coordinate type of the target : {target.status["coordtype"]} is not defined')
        
        # Exposure when not aborted
        if not self.abort_action.is_set():
            exposure = Exposure(Integrated_device = self.IDevice, abort_action = self.abort_action)
            for frame_number in range(count):
                exposure.run(frame_number = frame_number,
                            exptime = exptime,
                            filter_ = filter_,
                            imgtype = imgtype,
                            binning = binning,
                            target_name = target_name,
                            target = target
                            )
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
    