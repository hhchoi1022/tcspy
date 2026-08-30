#%%
from multiprocessing import Event
from multiprocessing import Manager
from threading import Thread
import time
import os
import glob
import numpy as np
from astropy.io import fits
from astropy.time import Time
import astropy.units as u

from tcspy.configuration import mainConfig
from tcspy.devices import MultiTelescopes
from tcspy.devices import SingleTelescope

from tcspy.utils.exception import *
from tcspy.action import MultiAction
from tcspy.action.level1 import Exposure
from tcspy.action.level2 import AutoFlat
from tcspy.action.level1 import SlewAltAz

from tcspy.devices import multitelescopes
#%%

class FilterCheck(mainConfig):

    def __init__(self,
                 multitelescopes : MultiTelescopes,
                 abort_action : Event,
                 ):
        super().__init__()
        self.multitelescopes = multitelescopes
        self.abort_action = abort_action
        self.is_running = False
        self.result = None
        
    def run(self, exptime : int  = 1):
        """
        Starts the filtercheck process in a separate thread (non-blocking).
        Poll is_running to wait for completion, then read self.result
        ((skylevel_dict, problematic_units); None means the check failed).
        """
        # Set BEFORE starting the thread so a supervisor polling is_running
        # right after run() cannot see a not-yet-started state.
        self.is_running = True
        filtercheck_thread = Thread(target=self._process, kwargs = dict(exptime = exptime))
        filtercheck_thread.start()
        
    def abort(self):
        """
        Aborts the startup process.
        """
        self.is_running = False
        self.abort_action.set()
        self.multitelescopes.log.warning(f'[{type(self).__name__}] is aborted.')  
        raise AbortionException(f'[{type(self).__name__}] is aborted.')  
    
    def _process(self, exptime : int = 1):
        self.is_running = True
        try:
            self.multitelescopes.register_logfile()
            self.multitelescopes.update_statusfile(status = 'busy', do_trigger = True)
            self.multitelescopes.log.info(f'[{type(self).__name__}] is triggered.')

            #Prepare for MultiAction for Slew
            params_slew_all = []

            for telescope_name, telescope in self.multitelescopes.devices.items():
                params_slew = dict(alt = 80, az = 300)
                params_slew_all.append(params_slew)
            self.multiaction = MultiAction(array_telescope= self.multitelescopes.devices.values(), array_kwargs= params_slew_all, function = SlewAltAz, abort_action = self.abort_action)
            self.shared_memory = self.multiaction.shared_memory

            # Slew
            try:
                self.multiaction.run()
            except AbortionException:
                self.abort()
            except ActionFailedException:
                for tel_name, result in self.shared_memory.items():
                    is_succeeded = self.shared_memory[tel_name]['succeeded']
                    if is_succeeded:
                        self.multitelescopes.log_dict[tel_name].info(f'[{type(self).__name__}] is finished')
                    else:
                        self.multitelescopes.log_dict[tel_name].info(f'[{type(self).__name__}] is failed')
                self.multitelescopes.log.critical(f'[{type(self).__name__}] is failed.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed.')

            filterset = ['g','r','i']
            expset = [exptime] * len(filterset)
            skylevel_dict = {}
            for filter_, exptime in zip(filterset, expset):
                skylevel_dict[filter_] = {}
                #Prepare for MultiAction for Exposure
                params_exposure_all = []
                for telescope_name, telescope in self.multitelescopes.devices.items():
                    params_exposure = dict(frame_number = 0, exptime = exptime, filter_ = filter_, gain = 2750, alt = 40, az = 300, name = 'filtercheck', objtype = 'test')
                    params_exposure_all.append(params_exposure)
                self.multiaction = MultiAction(array_telescope= self.multitelescopes.devices.values(), array_kwargs= params_exposure_all, function = Exposure, abort_action = self.abort_action)
                self.shared_memory = self.multiaction.shared_memory

                # Exposure
                try:
                    folder_key = (Time.now() - 12 * u.hour).datetime.strftime('%Y-%m-%d*')
                    self.multiaction.run()
                except AbortionException:
                    self.abort()
                except ActionFailedException:
                    for tel_name, result in self.shared_memory.items():
                        is_succeeded = self.shared_memory[tel_name]['succeeded']
                        if is_succeeded:
                            self.multitelescopes.log_dict[tel_name].info(f'[{type(self).__name__}] is finished')
                        else:
                            self.multitelescopes.log_dict[tel_name].info(f'[{type(self).__name__}] is failed')
                    self.multitelescopes.log.critical(f'[{type(self).__name__}] is failed.')
                    raise ActionFailedException(f'[{type(self).__name__}] is failed.')

                # Get the image count for each telescope
                for telescope_name, telescope in self.multitelescopes.devices.items():
                    # Filter-qualified pattern: leftover files from another filter
                    # (or a previous crashed run) must not be picked up.
                    key = os.path.join(telescope.config['IMAGE_PATH'], folder_key, f'*filtercheck_{filter_}_*.fits')
                    fits_file = glob.glob(key)
                    header_key = os.path.join(telescope.config['IMAGE_PATH'], folder_key, f'*filtercheck_{filter_}_*.head')
                    header_file = glob.glob(header_key)
                    if len(fits_file) == 0:
                        self.multitelescopes.log_dict[telescope_name].warning(f'[{type(self).__name__}] No filtercheck image found for {telescope_name} (pattern: {key}). This unit is skipped.')
                        continue
                    data = fits.getdata(fits_file[0])
                    mean = int(np.median(data))
                    print(f'{telescope_name} : {mean}')
                    os.remove(fits_file[0])
                    if len(header_file) > 0:
                        os.remove(header_file[0])
                    skylevel_dict[filter_][telescope_name] = mean
                    if os.listdir(os.path.dirname(fits_file[0])) == []:
                        os.rmdir(os.path.dirname(fits_file[0]))

            all_problematic_units = np.array([])
            for filter_, skylevel_info in skylevel_dict.items():
                telnames = list(skylevel_info.keys())
                skylevels = list(skylevel_info.values())
                if len(skylevels) == 0:
                    continue
                std = np.std(skylevels)
                idx = np.where(np.abs(np.array(skylevels) - np.mean(skylevels)) > 5 * std)
                problem_units = np.array(telnames)[idx]
                if problem_units.size > 0:
                    self.multitelescopes.log.critical(f'{filter_} band level is wired for the units: {problem_units}')
                    self.multitelescopes.log.critical(f'SKYLEVEL = {skylevel_dict[filter_]}')
                all_problematic_units = np.concatenate((all_problematic_units, problem_units))
            final_problematic_units = set(all_problematic_units)

            self.multitelescopes.log.info(f'[{type(self).__name__}] is finished.')
            self.result = skylevel_dict, final_problematic_units
            return skylevel_dict, final_problematic_units
        except AbortionException:
            raise
        except Exception as e:
            self.multitelescopes.log.critical(f'[{type(self).__name__}] is failed: {e}')
            raise
        finally:
            # Guarantee state recovery on EVERY exit path: a supervisor polling
            # is_running must never wait forever on a dead thread.
            try:
                self.multitelescopes.update_statusfile(status = 'idle', do_trigger = True)
            except Exception:
                pass
            self.is_running = False


# %%
if __name__ == '__main__':
    import argparse
    from tcspy.devices import MultiTelescopes
    from tcspy.utils.connector import SlackConnector
    from tcspy.utils import NightSession
    from tcspy.configuration import mainConfig
    # Argument parser for command-line exptime input
    parser = argparse.ArgumentParser(description="Run FilterCheck with specified exposure time.")
    parser.add_argument("--exptime", type=float, required=True, help="Exposure time in seconds.")
    args = parser.parse_args()
    
    M = MultiTelescopes()
    # Update config not to return log file
    original_config = []
    for tel in M.devices.values():
        config = mainConfig(tel.unitnum)
        original_config.append(config.config['IMAGE_SAVELOG'])
        config.update_config('IMAGE_SAVELOG', False)
        
    multitelescopes = MultiTelescopes()
    abort_action = Event()
    application = FilterCheck(multitelescopes, abort_action)
    try:
        slack = SlackConnector(token_path= application.config['SLACK_TOKEN'], default_channel_id= application.config['SLACK_DEFAULT_CHANNEL'])
        obsnight = NightSession(Time.now()).obsnight_utc
        tonight_str = '%.4d-%.2d-%.2d'%(obsnight.sunrise_civil.datetime.year, obsnight.sunrise_civil.datetime.month, obsnight.sunrise_civil.datetime.day)
        #message_ts = None
        message_ts = slack.get_message_ts(match_string = f'7DT Observation on {tonight_str}')
        if message_ts:
            slack.post_thread_message(message_ts,f'{type(application).__name__} is triggered: {time.strftime("%H:%M:%S", time.localtime())}')
    except:
        pass
    result= application.run(exptime = args.exptime)
    while application.is_running:
        time.sleep(0.1)
    try:
        if message_ts:
            slack.post_thread_message(message_ts,f'{type(application).__name__} is finished: {time.strftime("%H:%M:%S", time.localtime())}')
        if message_ts:
            slack.post_thread_message(message_ts,f'{type(application).__name__} is finished: {time.strftime("%H:%M:%S", time.localtime())}')
            skylevel_str = '\n'.join([f'*{band}*: ' + ', '.join([f'{telescope}: {value} \n' for telescope, value in telescopes.items()])
                                    for band, telescopes in result[0].items()])
            slack.post_thread_message(message_ts, f'Skylevel:\n{skylevel_str}')
    except:
        pass
    # Update config to original
    for tel, config_value in zip(M.devices.values(), original_config):
        config = mainConfig(tel.unitnum)
        config.update_config('IMAGE_SAVELOG', True)
# %%
