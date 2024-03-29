

#%%
from threading import Event
import time
import threading


from tcspy.configuration import mainConfig
from tcspy.devices import SingleTelescope
from tcspy.devices import MultiTelescopes
from tcspy.utils.exception import *

from tcspy.action.level1 import Warm
from tcspy.action.level1 import SlewAltAz
from tcspy.action import MultiAction

#%%

class Shutdown(mainConfig):
    """
    A class representing the shutdown process for multiple telescopes.

    Parameters
    ----------
    multitelescopes : MultiTelescopes
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
        Starts the shutdown process in a separate thread.
    abort()
        Aborts the shutdown process.
    """
    
    def __init__(self,
                 MultiTelescopes,
                 abort_action : Event,
                 ):
        super().__init__()
        self.multitelescopes = MultiTelescopes
        self.devices = MultiTelescopes.devices
        self.log = MultiTelescopes.log
        self.abort_action = abort_action
    
    def run(self):
        """
        Starts the startup process in a separate thread.
        """
        startup_thread = threading.Thread(target=self._process)
        startup_thread.start()
    
    def abort(self):
        """
        Aborts the startup process.
        """
        self.abort_action.set()
        for telescope_name, telescope in self.devices.items():
            self.log[telescope_name].warning(f'[{type(self).__name__}] is aborted.')
            
    def _process(self):

        # Telescope slewing
        params_slew = []
        for telescope_name, telescope in self.devices.items():
            self.log[telescope_name].info(f'[{type(self).__name__}] is triggered.')
            params_slew.append(dict(alt = self.config['SHUTDOWN_ALT'],
                                    az = self.config['SHUTDOWN_AZ']))
        multi_slew = MultiAction(array_telescope= self.devices.values(), array_kwargs= params_slew, function = SlewAltAz, abort_action = self.abort_action)
        multi_slew.run()
        result_multi_slew = multi_slew.get_results().copy()
        timeout = 60
        start_time = time.time()
        while all(key in result_multi_slew for key in self.devices) == False:
            if time.time() - start_time > timeout:
                print("Timeout")
                break
            time.sleep(1)
            result_multi_slew = multi_slew.get_results().copy()
            if self.abort_action.is_set():
                self.abort()
                for telescope_name, telescope in self.devices.items():
                    self.log[telescope_name].warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
        no_response_device = set(self.devices.keys())-set(result_multi_slew.keys())
        action_failed_device = set([key for key, value in result_multi_slew.items() if value == False])
        device_to_remove = no_response_device | action_failed_device
        if len(device_to_remove) > 0:
            for telescope_name in device_to_remove:
                self.log[telescope_name].critical(f'[{type(self).__name__}] is failed: Slewing failure.')
                self.multitelescopes.remove(telescope_name)

        # Check abort_action
        if self.abort_action.is_set():
            self.abort()
            for telescope_name, telescope in self.devices.items():
                self.log[telescope_name].warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')

        # Camera warming 
        params_warm = []
        for telescope_name, telescope in self.devices.items():
            params_warm.append(dict(settemperature = self.config['SHUTDOWN_CCDTEMP'],
                                    tolerance = self.config['SHUTDOWN_CCDTEMP_TOLERANCE']))
        multi_warm = MultiAction(array_telescope= self.devices.values(), array_kwargs= params_warm, function = Warm, abort_action = self.abort_action)
        multi_warm.run()
        result_multi_warm = multi_warm.get_results().copy()
        timeout = 600
        start_time = time.time()
        while all(key in result_multi_warm for key in self.devices) == False:
            if time.time() - start_time > timeout:
                print("Timeout")
                break
            time.sleep(1)
            result_multi_warm = multi_warm.get_results().copy()
            if self.abort_action.is_set():
                self.abort()
                for telescope_name, telescope in self.devices.items():
                    self.log[telescope_name].warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
        no_response_device = set(self.devices.keys())-set(result_multi_warm.keys())
        action_failed_device = set([key for key, value in result_multi_warm.items() if value == False])
        device_to_remove = no_response_device | action_failed_device
        if len(device_to_remove) > 0:
            for telescope_name in device_to_remove:
                self.log[telescope_name].critical(f'[{type(self).__name__}] is failed: Warming failure.')
                self.multitelescopes.remove(telescope_name)
        
        for telescope_name, telescope in self.devices.items():
            self.log[telescope_name].info(f'[{type(self).__name__}] is finished.')
    

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
    S = ShutDown(M, abort_action = abort_action)
    S.run()
    
    
# %%
