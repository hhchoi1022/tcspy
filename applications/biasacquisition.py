

#%%
from multiprocessing import Event
from threading import Thread
import uuid
import time

from tcspy.configuration import mainConfig
from tcspy.devices import MultiTelescopes
from tcspy.devices import SingleTelescope

from tcspy.utils.exception import *

from tcspy.action import MultiAction
from tcspy.action.level1 import Exposure
#%%

class BiasAcquisition(mainConfig):

    def __init__(self,
                 multitelescopes : MultiTelescopes,
                 abort_action : Event,
                 ):
        super().__init__()
        self.multitelescopes = multitelescopes
        self.abort_action = abort_action
        self.is_running = False
        
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
        self.is_running = False
        self.abort_action.set()
        
    def _process(self, 
                 count, 
                 binning : int = 1, 
                 gain : int = 2750):
        self.is_running = True
        self.multitelescopes.register_logfile()
        self.multitelescopes.update_statusfile(status = 'busy', do_trigger = True)
        self.multitelescopes.log.info(f'[{type(self).__name__}] is triggered.')

        id_ = uuid.uuid4().hex
        for i in range(count):
            params_exposure_all = []
            for telescope_name, telescope in self.multitelescopes.devices.items():
                params_exposure = dict(frame_number = i,
                                       exptime = 0,
                                       filter_ = None,
                                       imgtype = 'BIAS',
                                       binning = binning,
                                       gain = gain,
                                       obsmode = 'Single',
                                       objtype = 'BIAS',
                                       name = 'BIAS',
                                       id_ = id_
                                       ) 
                params_exposure_all.append(params_exposure)
            multi_exposure =MultiAction(array_telescope= self.multitelescopes.devices.values(), array_kwargs= params_exposure_all, function = Exposure, abort_action = self.abort_action)    
            result_multi_exposure = multi_exposure.shared_memory
            #Run
            try:
                multi_exposure.run()
            except AbortionException:
                self.multitelescopes.log.warning(f'[{type(self).__name__}] is aborted.')    
                self.is_running = False
                raise AbortionException(f'[{type(self).__name__}] is aborted.')  
        self.multitelescopes.log.info(f'[{type(self).__name__}] is finished.')
        self.multitelescopes.update_statusfile(status = 'idle', do_trigger = True)
        self.is_running = False

        
# %%
if __name__ == '__main__':
    
    import argparse
    from tcspy.devices import MultiTelescopes
    from tcspy.utils.connector import SlackConnector
    from tcspy.utils import NightSession
    from tcspy.configuration import mainConfig
    
    # Argument parser for command-line exptime input
    # parser = argparse.ArgumentParser(description="Run Bias Acquisition.")
    # parser.add_argument("--count", type=int, required=True, help="Number of images to acquire.")
    # parser.add_argument("--gain", type=int, default=2750, help="Gain value (default: 2750).")
    # parser.add_argument("--binning", type=int, default=1, help="Binning value (default: 1).")

    # args = parser.parse_args()
    
    M = MultiTelescopes()
    # Update config not to return log file
    original_config = []
    for tel in M.devices.values():
        config = mainConfig(tel.unitnum)
        original_config.append(config.config['IMAGE_SAVELOG'])
        config.update_config('IMAGE_SAVELOG', False)
    M = MultiTelescopes()
    abort_action = Event()
    application = BiasAcquisition(M, abort_action)
    slack = SlackConnector(token_path= application.config['SLACK_TOKEN'], default_channel_id= application.config['SLACK_DEFAULT_CHANNEL'])
    obsnight = NightSession().obsnight_utc
    tonight_str = '%.4d-%.2d-%.2d'%(obsnight.sunrise_civil.datetime.year, obsnight.sunrise_civil.datetime.month, obsnight.sunrise_civil.datetime.day)
    message_ts = slack.get_message_ts(match_string = f'7DT Observation on {tonight_str}')
    if message_ts:
        slack.post_thread_message(message_ts,f'{type(application).__name__} is triggered: {time.strftime("%H:%M:%S", time.localtime())}')
    application.run(count = 1, binning = 1, gain =2750)
    while application.is_running:
        time.sleep(0.1)
    if message_ts:
        slack.post_thread_message(message_ts,f'{type(application).__name__} is finished: {time.strftime("%H:%M:%S", time.localtime())}')

    # Update config to original
    for tel, config_value in zip(M.devices.values(), original_config):
        config = mainConfig(tel.unitnum)
        config.update_config('IMAGE_SAVELOG', config_value)
# %%
