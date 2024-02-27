#%%
from threading import Event

from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from tcspy.interfaces import *
from tcspy.utils.error import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.target import mainTarget
from tcspy.action.level1 import SlewRADec
from tcspy.action.level1 import SlewAltAz
from tcspy.action.level1 import Exposure
from tcspy.action.level1 import ChangeFocus
from tcspy.action.level1 import ChangeFilter
from tcspy.action.level2 import AutoFocus
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

    def _get_exposure_info(self,
                           filter_str : str,
                           exptime_str : str,
                           count_str : str,
                           binning_str : str):
        exptime_list = exptime_str.split(',')
        count_list = count_str.split(',')
        binning_list = binning_str.split(',')
        exposure_info = dict()
        if filter_str == None:
            exposure_info['filter'] = filter_str
            exposure_info['exptime'] = exptime_list[0]
            exposure_info['count'] = count_list[0]
            exposure_info['binning'] = binning_list[0]
        else:
            filter_list = filter_str.split(',')
            len_filt = len(filter_list)        
            for name, value in exposure_info.items():
                len_value = len(value)
                if len_filt != len_value:
                    exposure_info[name] = [value[0]] * len_filt
        return exposure_info
    
    def run(self, 
            exptime_str : str,
            count_str : str,
            filter_str : str = None, # When filter_str == None: Exposure with current filter
            binning_str : str = '1',
            imgtype : str = 'Light',
            ra : float = None, # When radec == None: do not move 
            dec : float = None,
            alt : float = None, # When altaz == None: do not move 
            az : float = None,
            target_name : str = None,
            obsmode : str = 'Single',
            autofocus_before_start : bool = False,
            autofocus_when_filterchange : bool = False
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
        
        target = mainTarget(unitnum = self.IDevice.unitnum, observer = self.IDevice.observer, target_ra = ra, target_dec = dec, target_alt = alt, target_az = az, target_name = target_name, target_obsmode = obsmode)
         
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

        # Get exposure information
        exposure_info = self._get_exposure_info(filter_str= filter_str, exptime_str= exptime_str, count_str= count_str, binning_str= binning_str)
        filter_info = exposure_info['filter']
        exptime_info = exposure_info['exptime']
        count_info = exposure_info['count']
        binning_info = exposure_info['binning']

        # Autofocus before beginning the first observation set 
        if autofocus_before_start:
            try:
                filter_ = filter_info[0]
                result_autofocus = AutoFocus(Integrated_device= self.IDevice, abort_action= self.abort_action).run(filter_ = filter_, use_offset = True)
            except ConnectionException:
                self._log.critical(f'[{type(self).__name__}] is failed: Device connection is lost.')
                raise ConnectionException(f'[{type(self).__name__}] is failed: Device connection is lost.')
            except AbortionException:
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
            except ActionFailedException:
                self._log.warning(f'[{type(self).__name__}] is failed: Autofocus is failed. Return to the previous focus value')
                pass
            
        result_all_exposure = []
        for filter_, exptime, count, binning in zip(filter_info, exptime_info, count_info, binning_info):
            info_filterwheel = self.IDevice.filterwheel.get_status()
            current_filter = info_filterwheel['filter']
            is_filter_changed = (current_filter != filter_)
            
            if is_filter_changed:
                # Filterchange
                try:    
                    result_filterchange = ChangeFilter(Integrated_device= self.IDevice, abort_action= self.abort_action).run(filter_ = filter_)
                except ConnectionException:
                    self._log.critical(f'[{type(self).__name__}] is failed: Filterwheel is disconnected.')                
                    raise ConnectionException(f'[{type(self).__name__}] is failed: Filterwheel is disconnected.')                
                except AbortionException:
                    self._log.warning(f'[{type(self).__name__}] is aborted.')
                    raise AbortionException(f'[{type(self).__name__}] is aborted.')
                except ActionFailedException:
                    self._log.critical(f'[{type(self).__name__}] is failed: Filterwheel movement failure.')
                    raise ActionFailedException(f'[{type(self).__name__}] is failed: Filterwheel movement failure.')
                
                # Apply offset
                offset = self.IDevice.filterwheel.get_offset_from_currentfilt(filter_ = filter_)
                self._log(f'Focuser is moving with the offset of {offset}[{current_filter} >>> {filter_}]')
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
                
                # Autofocus when filter changed
                if autofocus_when_filterchange:
                    try:
                        result_autofocus = AutoFocus(Integrated_device= self.IDevice, abort_action = self.abort_action).run(filter_ = filter_, use_offset = False)
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
            
            # Exposure
            exposure = Exposure(Integrated_device = self.IDevice, abort_action = self.abort_action)
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
    
# %%
IDevice = IntegratedDevice(1)
abort_action = Event()
S = SingleObservation(IDevice, abort_action)
# %%
S.run('5,5', '2,2', 'g,r', '1', ra = 240, dec = -15, autofocus_before_start = True, autofocus_when_filterchange= True)
# %%
