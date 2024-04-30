

#%%
from threading import Event
import time
from threading import Thread


from tcspy.configuration import mainConfig
from tcspy.devices import SingleTelescope
from tcspy.devices import MultiTelescopes
from tcspy.utils.exception import *

from tcspy.action.level1 import Warm
from tcspy.action.level1 import SlewAltAz
from tcspy.action import MultiAction

#%%

class Shutdown(mainConfig):
    
    def __init__(self,
                 MultiTelescopes,
                 abort_action : Event,
                 ):
        super().__init__()
        self.multitelescopes = MultiTelescopes
        self._log = MultiTelescopes.log
        self.abort_action = abort_action
    
    def run(self):
        startup_thread = Thread(target=self._process)
        startup_thread.start()
    
    def abort(self):
        self.abort_action.set()

    def _process(self):

        # Telescope slewing
        params_slew = []
        for telescope_name, telescope in self.multitelescopes.devices.items():
            self._log[telescope_name].info(f'[{type(self).__name__}] is triggered.')
            params_slew.append(dict(alt = self.config['SHUTDOWN_ALT'],
                                    az = self.config['SHUTDOWN_AZ']))
        
        multi_slew = MultiAction(array_telescope= self.multitelescopes.devices.values(), array_kwargs= params_slew, function = SlewAltAz, abort_action = self.abort_action)
        result_multi_slew = multi_slew.shared_memory
        
        ## Run
        try:
            multi_slew.run()
        except AbortionException:
            for tel_name in  self.multitelescopes.devices.keys():
                self._log[tel_name].warning(f'[{type(self).__name__}] is aborted.')
        
        ## Check result
        for tel_name, result in result_multi_slew.items():
            is_succeeded = result_multi_slew[tel_name]['succeeded']
            if not is_succeeded:
                self._log[tel_name].critical(f'[{type(self).__name__}] is failed: Slewing failure.')
                self.multitelescopes.remove(tel_name)        
        
        ## Check len(devices) > 0
        if len(self.multitelescopes.devices) == 0:
            raise ActionFailedException(f'[{type(self).__name__}] is Failed. Telescopes are not specified')
        
        ## Check abort_action
        if self.abort_action.is_set():
            for telescope_name, telescope in self.multitelescopes.devices.items():
                self._log[telescope_name].warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')

        # Warm camera
        params_warm = []
        for telescope_name, telescope in self.multitelescopes.devices.items():
            params_warm.append(dict(settemperature = self.config['SHUTDOWN_CCDTEMP'],
                                    tolerance = self.config['SHUTDOWN_CCDTEMP_TOLERANCE']))
        
        multi_warm = MultiAction(array_telescope= self.multitelescopes.devices.values(), array_kwargs= params_warm, function = Warm, abort_action = self.abort_action)
        result_multi_warm = multi_warm.shared_memory
        
        ## Run
        try:
            multi_warm.run()
        except AbortionException:
            for tel_name in  self.multitelescopes.devices.keys():
                self._log[tel_name].warning(f'[{type(self).__name__}] is aborted.')
        
        ## Check result
        for tel_name, result in result_multi_warm.items():
            is_succeeded = result_multi_warm[tel_name]['succeeded']
            if not is_succeeded:
                self._log[tel_name].critical(f'[{type(self).__name__}] is failed: Warming failure.')
                self.multitelescopes.remove(tel_name)        
        
        ## Check len(devices) > 0
        if len(self.multitelescopes.devices) == 0:
            raise ActionFailedException(f'[{type(self).__name__}] is Failed. Telescopes are not specified')
        
        for telescope_name, telescope in self.multitelescopes.devices.items():
            self._log[telescope_name].info(f'[{type(self).__name__}] is finished.')


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
                         SingleTelescope(10),
                         SingleTelescope(11),
                        ]
    
    print(time.time() - start)
    M = MultiTelescopes(list_telescopes)
    abort_action = Event()
    S = Shutdown(M, abort_action = abort_action)
    S.run()
    
    
# %%
