

#%%
from multiprocessing import Event
import time
from threading import Thread


from tcspy.configuration import mainConfig
from tcspy.devices import SingleTelescope
from tcspy.devices import MultiTelescopes
from tcspy.utils.exception import *

from tcspy.action.level1 import Cool
from tcspy.action.level1 import Connect
from tcspy.action.level1 import SlewAltAz
from tcspy.action import MultiAction

#%%

class Startup(mainConfig):
    """
    A class representing the startup process for multiple telescopes.

    Parameters
    ----------
    MultiTelescopes : MultiTelescopes
        An instance of MultiTelescopes class representing a collection of telescopes.
    abort_action : Event
        An instance of the built-in Event class to handle the abort action.

    Attributes
    ----------
    multitelescopes : MultiTelescopes
        The MultiTelescopes instance on which the action has to be performed.
    devices : devices
        The devices associated with the multiple telescopes.
    log : log
        Logging details of the operation.
    abort_action : Event
        An instance of Event to handle the abort action.

    Methods
    -------
    run()
        Starts the startup process in a separate thread.
    abort()
        Aborts the startup process.
    """
    
    def __init__(self,
                 multitelescopes,
                 abort_action : Event,
                 ):
        super().__init__()
        self.multitelescopes = multitelescopes
        self.abort_action = abort_action
    
    def run(self):
        """
        Starts the startup process in a separate thread.
        """
        startup_thread = Thread(target=self._process)
        startup_thread.start()

    def abort(self):
        """
        Aborts the startup process.
        """
        self.abort_action.set()
    
    def _process(self):
        """
        Performs the necessary steps to startup the telescopes.

        Raises
        ------
        AbortionException
            If the abortion event is triggered during the startup process.
        """
        # Connect
        params_connect = []
        self.multitelescopes.log.info(f'[{type(self).__name__}] is triggered.')
        for telescope_name, telescope in self.multitelescopes.devices.items():
            params_connect.append(dict())
        
        multi_connect =MultiAction(array_telescope= self.multitelescopes.devices.values(), array_kwargs= params_connect, function = Connect, abort_action = self.abort_action)    
        result_multi_connect = multi_connect.shared_memory
        
        ## Run
        try:
            multi_connect.run()
        except AbortionException:
            self.multitelescopes.log.warning(f'[{type(self).__name__}] is aborted.')
        
        ## Check result
        for tel_name, result in result_multi_connect.items():
            is_succeeded = result_multi_connect[tel_name]['succeeded']
            if not is_succeeded:
                self.multitelescopes.log_dict[tel_name].critical(f'[{type(self).__name__}] is failed: Connection failure.')
                self.multitelescopes.remove(tel_name)        
        
        ## Check len(devices) > 0
        if len(self.multitelescopes.devices) == 0:
            raise ActionFailedException(f'[{type(self).__name__}] is Failed. Telescopes are not specified')
        
        ## Check abort_action
        if self.abort_action.is_set():
            self.multitelescopes.log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
        
        # Telescope slewing
        params_slew = []
        for telescope_name, telescope in self.multitelescopes.devices.items():
            params_slew.append(dict(alt = self.config['STARTUP_ALT'],
                                    az = self.config['STARTUP_AZ']))
        
        multi_slew = MultiAction(array_telescope= self.multitelescopes.devices.values(), array_kwargs= params_slew, function = SlewAltAz, abort_action = self.abort_action)
        result_multi_slew = multi_slew.shared_memory
        
        ## Run
        try:
            multi_slew.run()
        except AbortionException:
            self.multitelescopes.log.warning(f'[{type(self).__name__}] is aborted.')

        ## Check result
        for tel_name, result in result_multi_slew.items():
            is_succeeded = result_multi_slew[tel_name]['succeeded']
            if not is_succeeded:
                self.multitelescopes.log_dict[tel_name].critical(f'[{type(self).__name__}] is failed: Slewing failure.')
                self.multitelescopes.remove(tel_name)        

        ## Check len(devices) > 0
        if len(self.multitelescopes.devices) == 0:
            raise ActionFailedException(f'[{type(self).__name__}] is Failed. Telescopes are not specified')
        
        ## Check abort_action
        if self.abort_action.is_set():
            self.multitelescopes.log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')

        # Camera cooling 
        params_cool = []
        for telescope_name, telescope in self.multitelescopes.devices.items():
            params_cool.append(dict(settemperature = self.config['STARTUP_CCDTEMP'],
                                    tolerance = self.config['STARTUP_CCDTEMP_TOLERANCE']))
        
        multi_cool = MultiAction(array_telescope= self.multitelescopes.devices.values(), array_kwargs= params_cool, function = Cool, abort_action = self.abort_action)
        result_multi_cool = multi_cool.shared_memory
        
        ## Run
        try:
            multi_cool.run()
        except AbortionException:
            self.multitelescopes.log.warning(f'[{type(self).__name__}] is aborted.')

        ## Check result
        for tel_name, result in result_multi_slew.items():
            is_succeeded = result_multi_slew[tel_name]['succeeded']
            if not is_succeeded:
                self.multitelescopes.log_dict[tel_name].critical(f'[{type(self).__name__}] is failed: Cooling failure.')
                self.multitelescopes.remove(tel_name)        
        ## Check len(devices) > 0
        if len(self.multitelescopes.devices) == 0:
            raise ActionFailedException(f'[{type(self).__name__}] is Failed. Telescopes are not specified')
        
        for tel_name, telescope in self.multitelescopes.devices.items():
            self.multitelescopes.log_dict[tel_name].info(f'[{type(self).__name__}] is finished.')
    

# %%
if __name__ == '__main__':
    import time
    start = time.time()
    list_telescopes = [SingleTelescope(1),
                         SingleTelescope(2),
                         SingleTelescope(3),
                         SingleTelescope(5),
                         SingleTelescope(6),
                         SingleTelescope(7),
                         SingleTelescope(8),
                         SingleTelescope(9),
                         #SingleTelescope(10),
                         SingleTelescope(11),
                        ]
    
    print(time.time() - start)
#%%

#%%
if __name__ == '__main__':
    start = time.time()

    M = MultiTelescopes(list_telescopes)
    start = time.time()
    M.status
    print(time.time() - start)
    abort_action = Event()
    S = Startup(M, abort_action = abort_action)
#%%
        
