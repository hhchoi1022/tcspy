

#%%
from multiprocessing import Event
from threading import Thread

from tcspy.configuration import mainConfig
from tcspy.devices import MultiTelescopes
from tcspy.utils.exception import *

from tcspy.action import MultiAction
from tcspy.action.level2 import SingleObservation


#%%

class BiasAcquisition(mainConfig):


    def __init__(self,
                 multitelescopes : MultiTelescopes,
                 abort_action : Event,
                 ):
        super().__init__()
        self.multitelescopes = multitelescopes
        self.abort_action = abort_action
        
    def run(self,
            count : int = 9,
            binning = 1,
            gain : int = 2750):
        """
        Starts the startup process in a separate thread.
        """
        startup_thread = Thread(target=self._process, kwargs = dict(count = count, binning = binning, gain = gain))
        startup_thread.start()
        
        
    def abort(self):
        """
        Aborts the startup process.
        """
        self.abort_action.set()
        
    def _process(self, count, binning, gain):
        params_singleobs = []
        self.multitelescopes.log.info(f'[{type(self).__name__}] is triggered.')
        for telescope_name, telescope in self.multitelescopes.devices.items():
            params_singleobs_for_bias = dict(exptime = 0,
                                             count = count,
                                             filter_ = None,
                                             binning = binning,
                                             gain = gain,
                                             imgtype = 'BIAS',
                                             autofocus_use_history = False,
                                             autofocus_history_duration = 60,
                                             autofocus_before_start = False,
                                             autofocus_when_filterchange = False,
                                             autofocus_when_elapsed = False,
                                             autofocus_elapsed_duration = 60
                                             ) 
            params_singleobs.append(params_singleobs_for_bias)
        multi_exposure =MultiAction(array_telescope= self.multitelescopes.devices.values(), array_kwargs= params_singleobs, function = SingleObservation, abort_action = self.abort_action)    
        result_multi_exposure = multi_exposure.shared_memory
        ## Run 
        try:
            multi_exposure.run()
        except AbortionException:
            self.multitelescopes.log.warning(f'[{type(self).__name__}] is aborted.')    
        