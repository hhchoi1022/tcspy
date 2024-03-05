#%%
from threading import Event
from typing import List, Union
import os, json

from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from tcspy.interfaces import *
from tcspy.utils.error import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.target import mainTarget
from tcspy.action import MultiAction

from tcspy.action.level2 import SingleObservation

from tcspy.utils.exception import *
#%%
class SpecObservation(Interface_Runnable, Interface_Abortable):
    def __init__(self, 
                 array_IntegratedDevice : List[IntegratedDevice],
                 abort_action : Event,
                 specmode_folder : str = '../../configuration/specmode/u10/'):
        self.IDevices_list = array_IntegratedDevice
        self.IDevices_dict = self._get_IDevices_dict()
        self.IDevices_status_dict = self._get_IDevice_status_dict()
        self.abort_action = abort_action
        self._specmode_folder = specmode_folder
        self._log = mainLogger(unitnum = self.IDevice.unitnum, logger_name = __name__+str(self.IDevice.unitnum)).log()
    
    def _get_IDevices_dict(self):
        IDevices_dict = dict()
        for IDevice in self.IDevices_list:
            name_IDevice = IDevice.name
            IDevices_dict[name_IDevice] = IDevice
        return IDevices_dict

    def _get_IDevice_status_dict(self):
        IDevices_status_dict = dict()
        for IDevice in self.IDevices_list:
            name_IDevice = IDevice.name
            IDevices_status_dict[name_IDevice] = DeviceStatus(IDevice)
        return IDevices_status_dict
    
    def _get_filters_from_specmodes(self,
                                    specmode : str):
        specmode_file = self._specmode_folder + f'{specmode}.specmode'
        is_exist_specmodefile = os.path.isfile(specmode_file)
        if is_exist_specmodefile:
            with open(specmode_file, 'r') as f:
                specmode_dict = json.load(f)
            return specmode_dict
        else:
            self._log.critical(f'Specmode[{specmode}] is not registered in "{self._specmode_folder}"')
            raise SpecmodeRegisterException(f'Specmode[{specmode}] is not registered in "{self._specmode_folder}"')
    
    def _format_kwargs(self,
                       filter_str : str,
                       exptime_str : str,
                       count_str : str,
                       binning_str : str = '1',
                       **kwargs):
        format_kwargs = dict()
        format_kwargs['filter_str'] = filter_str
        format_kwargs['exptime_str'] = exptime_str
        format_kwargs['count_str'] = count_str
        format_kwargs['binning_str'] = binning_str
        filter_list = format_kwargs['filter_str'].split(',')
        len_filt = len(filter_list)        
        
        # Exposure information
        for kwarg, value in format_kwargs.items():
            valuelist = value.split(',')
            if len_filt != len(valuelist):
                valuelist = [valuelist[0]] * len_filt
            formatted_value = ','.join(valuelist)
            format_kwargs[kwarg] = formatted_value
        # Other information
        for key, value in kwargs.items():
            format_kwargs[key] = value
        return format_kwargs
    
    def run(self, 
            exptime_str : str,
            count_str : str,
            specmode : str,
            binning_str : str = '1',
            imgtype : str = 'Light',
            ra : float = None,
            dec : float = None,
            alt : float = None,
            az : float = None,
            target_name : str = None,
            autofocus_before_start : bool = True,
            autofocus_when_filterchange : bool = True
            ):
        
        # Check condition of the instruments for this Action
        status_all_telescopes = self.IDevices_status_dict()
        for IDevice_name, IDevice_status in status_all_telescopes.items():
            status_filterwheel = IDevice_status['filterwheel']
            status_camera = IDevice_status['camera']
            status_telescope = IDevice_status['telescope']
            status_focuser = IDevice_status['focuser']
            if status_filterwheel.lower() == 'dicconnected':
                self._log.critical(f'{IDevice_name} filterwheel is disconnected.')
            if status_camera.lower() == 'dicconnected':
                self._log.critical(f'{IDevice_name} camera is disconnected.')
            if status_telescope.lower() == 'dicconnected':
                self._log.critical(f'{IDevice_name} telescope is disconnected.')
            if status_focuser.lower() == 'dicconnected':
                self._log.critical(f'{IDevice_name} focuser is disconnected.')
                
        # Abort when triggered
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise  AbortionException(f'[{type(self).__name__}] is aborted.')
        
        # Construct target instance
        target = mainTarget(unitnum = self.IDevice.unitnum, observer = self.IDevice.observer, target_ra = ra, target_dec = dec, target_alt = alt, target_az = az, target_name = target_name, target_obsmode = 'Spec')                
        
        # Get filter information
        specmode_dict = self._get_filters_from_specmodes(specmode = specmode)
        
        # Define parameters for SingleObservation module for all telescopes
        all_params_obs = dict()
        for IDevice_name, IDevice in self.IDevices_dict.items():
            filter_str = ','.join(specmode_dict[IDevice_name])
            params_obs = self._format_kwargs(filter_str = filter_str, exptime_str = exptime_str, count_str = count_str, binning_str = binning_str, imgtype = imgtype, ra = ra, dec = dec, alt = alt, az = az, target_name = target_name, obsmode = 'Spec', autofocus_before_start = autofocus_before_start, autofocus_when_filterchange = autofocus_when_filterchange)
            all_params_obs[IDevice_name] = params_obs
        
        # Run Multiple actions
        multiaction = MultiAction(array_telescope = self.IDevices_dict.values, array_kwargs = all_params_obs.values, function = SingleObservation)
        multiaction.run()
        
        '''
            result_telescope = False
            if not IDevice_name in specmode_dict.keys():
                raise SpecmodeRegisterException(f'{IDevice_name} is not registered in the specmode [{specmode}] file')
            else:            
                filter_str = ','.join(specmode_dict[IDevice_name])
                exposure_info = self._get_exposure_info(filter_str = filter_str, exptime_str = exptime_str, count_str = count_str, binning_str = binning_str)
                filter_info = exposure_info['filter']
                exptime_info = exposure_info['exptime']
                count_info = exposure_info['count']
                binning_info = exposure_info['binning']
                result_all_exposure = []
                for filter_, exptime, count, binning in zip(filter_info, exptime_info, count_info, binning_info):
                    observation = SingleObservation(Integrated_device= IDevice, abort_action = self.abort_action)
                    result_exposure = False
                    try:
                        result_exposure = observation.run(exptime = exptime, 
                                                          count = count, 
                                                          filter_ = filter_, 
                                                          imgtype = imgtype,
                                                          binning = binning,
                                                          ra = ra, 
                                                          dec = dec, 
                                                          target_name = target_name, 
                                                          target_obsmode = 'Spec', 
                                                          autofocus_before_start= autofocus_before_start, 
                                                          autofocus_when_filterchange = autofocus_when_filterchange)
                    except ConnectionException:
                        self._log.critical(f'[{type(self).__name__}] is failed: telescope is disconnected.')
                        raise ConnectionException(f'[{type(self).__name__}] is failed: telescope is disconnected.')
                    except AbortionException:
                        self._log.warning(f'[{type(self).__name__}] is aborted.')
                        raise AbortionException(f'[{type(self).__name__}] is aborted.')
                    except ActionFailedException:
                        self._log.critical(f'[{type(self).__name__}] is failed: slewing failure.')
                        raise ActionFailedException(f'[{type(self).__name__}] is failed: slewing failure.')
                    result_all_exposure.append(result_exposure)
                result_telescope = all(result_all_exposure)
            result_all_telescope[IDevice_name] = result_telescope
        return result_all_telescope        
    '''
            
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
