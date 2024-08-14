

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
from tcspy.action.level1 import Home
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
        self.is_running = False
    
    def run(self, 
            home : bool = True, 
            slew : bool = True,    
            cool : bool = True):
        """
        Starts the startup process in a separate thread.
        """
        startup_thread = Thread(target=self._process, kwargs = dict(home = home, slew = slew, cool = cool))
        startup_thread.start()

    def abort(self):
        """
        Aborts the startup process.
        """
        self.abort_action.set()
        self.is_running = False
    
    def _process(self, home, slew, cool):
        """
        Performs the necessary steps to startup the telescopes.

        Raises
        ------
        AbortionException
            If the abortion event is triggered during the startup process.
        """
        self.is_running = True
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
            self.is_running = False
            self.multitelescopes.log.warning(f'[{type(self).__name__}] is aborted.')
        
        ## Check result
        for tel_name, result in result_multi_connect.items():
            is_succeeded = result_multi_connect[tel_name]['succeeded']
            if not is_succeeded:
                self.multitelescopes.log_dict[tel_name].critical(f'[{type(self).__name__}] is failed: Connection failure.')
                self.multitelescopes.remove(tel_name)        
        
        ## Check len(devices) > 0
        if len(self.multitelescopes.devices) == 0:
            self.is_running = False
            raise ActionFailedException(f'[{type(self).__name__}] is Failed. Telescopes are not specified')
        
        ## Check abort_action
        if self.abort_action.is_set():
            self.is_running = False
            self.multitelescopes.log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
        
        if home:
            # Telescope homing
            params_home = []
            for telescope_name, telescope in self.multitelescopes.devices.items():
                params_home.append(dict())
            
            multi_home = MultiAction(array_telescope= self.multitelescopes.devices.values(), array_kwargs= params_home, function = Home, abort_action = self.abort_action)
            result_multi_home = multi_home.shared_memory
            
            ## Run
            try:
                multi_home.run()
                time.sleep(10)
            except AbortionException:
                self.is_running = False
                self.multitelescopes.log.warning(f'[{type(self).__name__}] is aborted.')

            ## Check result
            for tel_name, result in result_multi_home.items():
                is_succeeded = result_multi_home[tel_name]['succeeded']
                if not is_succeeded:
                    self.multitelescopes.log_dict[tel_name].critical(f'[{type(self).__name__}] is failed: Homing failure.')
                    self.multitelescopes.remove(tel_name)        

            ## Check len(devices) > 0
            if len(self.multitelescopes.devices) == 0:
                self.is_running = False
                raise ActionFailedException(f'[{type(self).__name__}] is Failed. Telescopes are not specified')
            
            ## Check abort_action
            if self.abort_action.is_set():
                self.is_running = False
                self.multitelescopes.log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
            
            
        if slew:
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
                self.is_running = False
                self.multitelescopes.log.warning(f'[{type(self).__name__}] is aborted.')

            ## Check result
            for tel_name, result in result_multi_slew.items():
                is_succeeded = result_multi_slew[tel_name]['succeeded']
                if not is_succeeded:
                    self.multitelescopes.log_dict[tel_name].critical(f'[{type(self).__name__}] is failed: Slewing failure.')
                    self.multitelescopes.remove(tel_name)        

            ## Check len(devices) > 0
            if len(self.multitelescopes.devices) == 0:
                self.is_running = False
                raise ActionFailedException(f'[{type(self).__name__}] is Failed. Telescopes are not specified')
            
            ## Check abort_action
            if self.abort_action.is_set():
                self.is_running = False
                self.multitelescopes.log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')

        if cool:
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
                self.is_running = False
                self.multitelescopes.log.warning(f'[{type(self).__name__}] is aborted.')

            ## Check result
            for tel_name, result in result_multi_slew.items():
                is_succeeded = result_multi_slew[tel_name]['succeeded']
                if not is_succeeded:
                    self.multitelescopes.log_dict[tel_name].critical(f'[{type(self).__name__}] is failed: Cooling failure.')
                    self.multitelescopes.remove(tel_name)        
            ## Check len(devices) > 0
            if len(self.multitelescopes.devices) == 0:
                self.is_running = False
                raise ActionFailedException(f'[{type(self).__name__}] is Failed. Telescopes are not specified')
            
        for tel_name, telescope in self.multitelescopes.devices.items():
            self.multitelescopes.log_dict[tel_name].info(f'[{type(self).__name__}] is finished.')
        self.is_running = False

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
#%%
if __name__ == '__main__':
    M = MultiTelescopes(list_telescopes)
    abort_action = Event()
    S = Startup(M, abort_action = abort_action)
    S.run(slew = False, cool = False)
#%%
if __name__ == '__main__':
    import schedule
    M = MultiTelescopes(list_telescopes)

    abort_action = Event()
    S = Startup(M, abort_action = abort_action)
    import schedule
    import time

    def job_that_executes_once():
        # Do some work that only needs to happen once...
        S.run()
        return schedule.CancelJob
    from tcspy.utils.databases import DB
    time_prepare = DB().Daily.obsnight.sunset_prepare.datetime
    time_prepare_str = '%.2d:%.2d'%(time_prepare.hour-3, time_prepare.minute)

    schedule.every().day.at(time_prepare_str).do(job_that_executes_once)
    

    while True:
        schedule.run_pending()
        time.sleep(1)
#%%
        
