

#%%
from multiprocessing import Event
from threading import Thread

from tcspy.configuration import mainConfig
from tcspy.devices import MultiTelescopes
from tcspy.utils.exception import *

from tcspy.action import MultiAction
from tcspy.action.level1 import Exposure


#%%

class DarkAcquisition(mainConfig):


    def __init__(self,
                 multitelescopes : MultiTelescopes,
                 abort_action : Event,
                 ):
        super().__init__()
        self.multitelescopes = multitelescopes
        self.abort_action = abort_action
        
    def run(self,
            count : int = 9,
            exptime : float = 100,
            gain : int = 2750):
        """
        Starts the startup process in a separate thread.
        """
        startup_thread = Thread(target=self._process, kwargs = dict(count = count, gain = gain, exptime = exptime))
        startup_thread.start()
        
        
    def abort(self):
        """
        Aborts the startup process.
        """
        self.abort_action.set()
        
    def _process(self, count, gain, exptime):
        params_exposure = []
        self.multitelescopes.log.info(f'[{type(self).__name__}] is triggered.')
        for telescope_name, telescope in self.multitelescopes.devices.items():
            params_exposure.append(dict(count = count, exptime = exptime, gain = gain))
        
        multi_exposure =MultiAction(array_telescope= self.multitelescopes.devices.values(), array_kwargs= params_exposure, function = Exposure, abort_action = self.abort_action)    
        result_multi_exposure = multi_exposure.shared_memory
    
        ## Run
        try:
            multi_exposure.run()
        except AbortionException:
            self.multitelescopes.log.warning(f'[{type(self).__name__}] is aborted.')    
        