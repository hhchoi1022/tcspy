#%%
from threading import Event

from tcspy.devices import IntegratedDevice
from tcspy.devices import MultiTelescopes
from tcspy.interfaces import *
from tcspy.utils.target import SingleTarget
from tcspy.utils.exception import *

from tcspy.action import MultiAction
from tcspy.action.level2 import SingleObservation

#%%
class DeepObservation(Interface_Runnable, Interface_Abortable):
    def __init__(self, 
                 MultiTelescopes : MultiTelescopes,
                 abort_action : Event):        
        self.multitelescopes = MultiTelescopes
        self.observer = list(self.multitelescopes.devices.values())[0].observer
        self.abort_action = abort_action
        self._log = MultiTelescopes.log
    
    def _format_params(self,
                       imgtype : str = 'Light',
                       autofocus_before_start = True,
                       autofocus_when_filterchange = True,
                       **kwargs):
        format_kwargs = dict()
        format_kwargs['imgtype'] = imgtype
        format_kwargs['autofocus_before_start'] = autofocus_before_start
        format_kwargs['autofocus_when_filterchange'] = autofocus_when_filterchange

        # Other information
        for key, value in kwargs.items():
            format_kwargs[key] = value
        return format_kwargs
    
    def run(self, 
            exptime : str,
            count : str,
            filter_ : str,
            binning : str = '1',
            imgtype : str = 'Light',
            ra : float = None,
            dec : float = None,
            alt : float = None,
            az : float = None,
            target_name : str = None,
            objtype : str = None,
            autofocus_before_start : bool = True,
            autofocus_when_filterchange : bool = True,
            ):
        
        """ Test
        exptime= '10,10'
        count= '5,5'
        filter_ = 'g,r'
        binning= '1,1'
        imgtype = 'Light'
        ra= '200.4440'
        dec= '-20.5520'
        alt = None
        az = None
        target_name = "NGC3147"
        objtype = 'ToO'
        autofocus_before_start= True
        autofocus_when_filterchange= True
        
        """
        
        # Check condition of the instruments for this Action
        status_multitelescope = self.multitelescopes.status
        for IDevice_name, IDevice_status in status_multitelescope.items():
            self._log[IDevice_name].info(f'[{type(self).__name__}] is triggered.')
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
        
        ntelescope = len(self.multitelescopes.devices)
        # Get target instance
        singletarget = SingleTarget(observer = self.observer,
                                    ra = ra, 
                                    dec = dec, 
                                    alt = alt, 
                                    az = az,
                                    name = target_name,
                                    objtype = objtype,
                                    
                                    exptime = exptime,
                                    count = count,
                                    filter_ = filter_,
                                    binning = binning,
                                    obsmode = 'Deep',
                                    ntelescope= ntelescope)                
        
        # Get filter information
        exposure_params = singletarget.exposure_info
        target_params = singletarget.target_info
        
        # Define parameters for SingleObservation module for all telescopes
        all_params_obs = dict()
        for IDevice_name, IDevice in self.multitelescopes.devices.items():
            params_obs = self._format_params(imgtype= imgtype, 
                                             autofocus_before_start= autofocus_before_start, 
                                             autofocus_when_filterchange= autofocus_when_filterchange, 
                                             **exposure_params,
                                             **target_params)
            params_obs.update(filter_ = filter_)
            all_params_obs[IDevice_name] = params_obs
        
        # Run Multiple actions
        multiaction = MultiAction(array_telescope = self.IDevices_dict.values(), array_kwargs = all_params_obs.values(), function = SingleObservation)
        multiaction.run()
        
        for IDevice_name, IDevice_status in status_multitelescope.items():
            self._log[IDevice_name].info(f'[{type(self).__name__}] is finished')

    def abort(self):
        self.abort_action.set()
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
IDevice_1 = IntegratedDevice(21)
#%%
abort_action = Event()
S  = DeepObservation([IDevice_1], abort_action)
# %%
