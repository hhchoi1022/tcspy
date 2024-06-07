#%%
from tcspy.configuration import mainConfig
from tcspy.action.level2 import AutoFocus
from tcspy.action import MultiAction
from tcspy.action.level1 import SlewAltAz
from tcspy.devices import SingleTelescope, MultiTelescopes
from multiprocessing import Event
from tcspy.utils.exception import *
import json
#%%



class AutofocusInitializer(mainConfig):
    
    def __init__(self,
                 multitelescopes : MultiTelescopes,
                 abort_action : Event,
                 ):
        super().__init__()
        self.multitelescopes = multitelescopes
        self.abort_action = abort_action
        self.filtinfo = self._get_filtinfo()
    
    def _get_filtinfo(self):
        with open(self.config['AUTOFOCUS_FILTINFO_FILE'], 'r') as f:
            filtinfo = json.load(f)
        return filtinfo
    
    def _process(self,
                 initial_filter : str = 'r'):
        
        self.multitelescopes.log.info(f'[{type(self).__name__}] is triggered.')
        # Slew 
        alt = 50
        az = 160
        tracking= True
        action_slew = MultiAction(self.multitelescopes.devices, dict(alt = alt, az = az, tracking = tracking), SlewAltAz, Event())
        try:
            action_slew.run()
        except ConnectionException:
            self.multitelescopes.log.critical(f'[{type(self).__name__}] is failed.')
            raise ConnectionException(f'[{type(self).__name__}] is failed.')
        except AbortionException:
            self.multitelescopes.log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
        except ActionFailedException:
            self.multitelescopes.log.critical(f'[{type(self).__name__}] is failed')
            raise ActionFailedException(f'[{type(self).__name__}] is failed.')
        # Run Autofocus
        max_length = max(len(lst) for lst in self.filtinfo.values())
        action_autofocus = MultiAction(list_telescopes, dict(filter_ = initial_filter, use_offset = True, use_history = True), AutoFocus, Event())
        result_autofocus = action_autofocus.shared_memory



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
mtel = MultiTelescopes(list_telescopes)
#%%
filtinfo_filepath = '../configuration/filtinfo.data'
with open(filtinfo_filepath, 'r') as f:
    filtinfo = json.load(f)
# Find the maximum length of the lists
max_length = max(len(lst) for lst in filtinfo.values())
# Extend each list to the maximum length by repeating its elements
for key, lst in filtinfo.items():
    if len(lst) < max_length:
        repeat_times = (max_length // len(lst)) + 1  # Determine how many times to repeat the list
        extended_list = (lst * repeat_times)[:max_length]  # Repeat and slice to the maximum length
        filtinfo[key] = extended_list
#%%
# %%

# %%
action_slew.run()
# %%


#%%
action_autofocus = MultiAction(list_telescopes, dict(filter_ = None), AutoFocus, Event())
# %%
action_autofocus.run()
# %%
from tcspy.action.level1 import *
ChangeFilter(SingleTelescope(1), Event()).run('m400')
# %%
AutoFocus(SingleTelescope(1), Event()).run()
# %%
from tcspy.action.level1 import Exposure
from tcspy.action.level1 import ChangeFocus

for i in range(3):
    action_exposure = MultiAction(list_telescopes, dict(frame_number = i, exptime = 10, filter_ = 'r', gain = 2750, alt = 50, az = 160, name = 'Defocus_test', objtype = 'Test', note ='Use this image for quality test' ))

#%%
