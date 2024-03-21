#%%
from threading import Event

from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from tcspy.interfaces import *
from tcspy.utils.error import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.target import SingleTarget
from tcspy.utils.exception import *

from tcspy.action.level1 import SlewRADec
from tcspy.action.level1 import SlewAltAz
from tcspy.action.level1 import Exposure
from tcspy.action.level1 import ChangeFocus
from tcspy.action.level1 import ChangeFilter
from tcspy.action.level2 import AutoFocus

#%%
class SingleObservation(Interface_Runnable, Interface_Abortable):
    def __init__(self, 
                 Integrated_device : IntegratedDevice,
                 abort_action : Event):
        self.IDevice = Integrated_device
        self.IDevice_status = DeviceStatus(self.IDevice)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.IDevice.unitnum, logger_name = __name__+str(self.IDevice.unitnum)).log()

    def _exposureinfo_to_list(self,
                              filter_ : str,
                              exptime : str,
                              count : str,
                              binning : str):
        exptime_list = exptime.split(',')
        count_list = count.split(',')
        binning_list = binning.split(',')
        exposure_info = dict()
        if filter_ == None:
            exposure_info['filter_'] = filter_
            exposure_info['exptime'] = exptime_list[0]
            exposure_info['count'] = count_list[0]
            exposure_info['binning'] = binning_list[0]
        else:
            filter_list = filter_.split(',')
            exposure_info['filter_'] = filter_list
            exposure_info['exptime'] = exptime_list
            exposure_info['count'] = count_list
            exposure_info['binning'] = binning_list
            len_filt = len(filter_list)        
            for name, value in exposure_info.items():
                len_value = len(value)
                if len_filt != len_value:
                    exposure_info[name] = [value[0]] * len_filt
        return exposure_info
    
    def run(self, 
            exptime : str,
            count : str,
            filter_ : str = None, # When filter_ == None: Exposure with current filter_
            binning : str = '1',
            imgtype : str = 'Light',
            ra : float = None, # When radec == None: do not move 
            dec : float = None,
            alt : float = None, # When altaz == None: do not move 
            az : float = None,
            target_name : str = None,
            obsmode : str = 'Single',
            specmode : str = None,
            ntelescope : int = 1,
            objtype : str = None,
            autofocus_before_start : bool = False,
            autofocus_when_filterchange : bool = False,
            **kwargs
            ):
        
        self._log.info(f'[{type(self).__name__}] is triggered.')

        """
        
        # Target 1
        exptime= '10,10'
        count= '5,5'
        filter_= 'm450,m475'
        binning= '1,1'
        imgtype = 'Light'
        ra= '200.4440'
        dec= '-20.5520'
        alt = None
        az = None
        target_name = "NGC3147"
        obsmode= 'Spec'
        specmode = 'specall'
        objtype = 'ToO'
        ntelescope = 1
        autofocus_before_start= True
        autofocus_when_filterchange= True
        
        exptime= '10,10'
        count= '5,5'
        filter_= 'g,r'
        binning= '1,1'
        imgtype = 'Light'
        ra= '200.4440'
        dec= '-20.5520'
        target_name = "NGC3147"
        obsmode= 'Single'
        specmode = None
        objtype = None
        autofocus_before_start= True
        autofocus_when_filterchange= True
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
            raise ConnectionException(f'[{type(self).__name__}] is failed: devices are disconnected.')
        # Done
        
        # Slewing when not aborted
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise  AbortionException(f'[{type(self).__name__}] is aborted.')
        
        # Set target
        target = SingleTarget(observer = self.IDevice.observer, 
                              ra = ra, 
                              dec = dec, 
                              alt = alt, 
                              az = az, 
                              name = target_name, 
                              objtype= objtype,
                              
                              exptime = exptime,
                              count = count,
                              filter_ = filter_,
                              binning = binning, 
                              obsmode = obsmode,
                              specmode = specmode,
                              ntelescope = ntelescope
                              )
        target_info = target.target_info
        exposure_info = target.exposure_info
         
        # Slewing
        if target.status['coordtype'] == 'radec':
            try:
                slew = SlewRADec(Integrated_device = self.IDevice, abort_action= self.abort_action)
                result_slew = slew.run(ra = float(target_info['ra']), dec = float(target_info['dec']))
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
                result_slew = slew.run(alt = float(target_info['alt']), az = float(target_info['az']))
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
        observation_params = self._exposureinfo_to_list(filter_ = exposure_info['filter_'], exptime = exposure_info['exptime'], count = exposure_info['count'], binning = exposure_info['binning'])
        filter_info = observation_params['filter_']
        exptime_info = observation_params['exptime']
        count_info = observation_params['count']
        binning_info = observation_params['binning']

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
                
                # Apply offset
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
        
            # Abort action when triggered
            if self.abort_action.is_set():
                self.abort()
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                raise  AbortionException(f'[{type(self).__name__}] is aborted.')
            
            # Exposure
            exposure = Exposure(Integrated_device = self.IDevice, abort_action = self.abort_action)
            for frame_number in range(int(count)):
                try:
                    result_exposure = exposure.run(frame_number = int(frame_number),
                                                    exptime = float(exptime),
                                                    filter_ = filter_,
                                                    imgtype = imgtype,
                                                    binning = int(binning),
                                                    obsmode = obsmode,
                                                    
                                                    ra = ra,
                                                    dec = dec,
                                                    alt = alt,
                                                    az = az,
                                                    target_name = target_name,
                                                    objtype = objtype)
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
            
        self._log.info(f'[{type(self).__name__}] is finished')
        
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
if __name__ == '__main__':
    from tcspy.action.level1 import Connect
    IDevice = IntegratedDevice(21)
    abort_action = Event()
    C = Connect(IDevice, abort_action)
    C.run()
    S = SingleObservation(IDevice, abort_action)
    S.run(exptime = '5,5', 
          count = '2,2', 
          filter_ = 'specall', 
          binning = '1', 
          imgtype = 'Light',
          ra = 256.5, 
          dec = -58.0666 , 
          obsmode = 'Spec',
          autofocus_before_start = False, 
          autofocus_when_filterchange= False)
# %%
