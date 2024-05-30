#%%
from tcspy.action.level2 import AutoFocus
from tcspy.action import MultiAction
from tcspy.action.level1 import SlewRADec
from tcspy.devices import SingleTelescope, MultiTelescopes
from multiprocessing import Event
#%%


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

# %%
ra = 227.27033
dec = -42.70497
tracking= True
action_slew = MultiAction(list_telescopes, dict(ra = ra, dec = dec, tracking = tracking), SlewRADec, Event())
# %%
action_slew.run()
# %%
action_autofocus = MultiAction(list_telescopes, dict(filter_ = 'r'), AutoFocus, Event())
# %%
action_autofocus.run()
# %%
from threading import Thread
from tcspy.action.level1 import Exposure
from tcspy.action.level1 import ChangeFocus
from tcspy.devices.weather import WeatherUpdater
abort_weather = Event()
Thread(target = WeatherUpdater().run, kwargs = dict(abort_action = abort_weather), daemon = True).start()

#%%
import time
offset = 0
for i in range(11):
    print(f'Start with {offset}')
    action_obs = DeepObservation(mtel, Event())
    action_obs.run(exptime = 10, count = 3, filter_ = 'r', ntelescope = 10, gain = 2750, ra = ra, dec = dec, name = 'Defocus_test_WASP-178b', objtype = 'Test',note = f'Focusval = Best + {offset}', autofocus_use_history = False)
    time.sleep(10)
    action_focus = MultiAction(list_telescopes, dict(position = 100, is_relative = True), ChangeFocus, Event())
    action_focus.run()
    time.sleep(10)
    offset += 100
#%%

from tcspy.action.level3 import DeepObservation

#%%
action_obs = DeepObservation(mtel, Event())
# %%
offset = 0

action_obs.run(exptime = 10, count = 3, filter_ = 'r', ntelescope = 10, gain = 2750, ra = ra, dec = dec, name = 'Defocus_test_WASP-178b', objtype = 'Test',note = f'Focusval = Best + {offset}', autofocus_use_history = False)
# %%
action_focus = MultiAction(list_telescopes, dict(position = 100, is_relative = True), ChangeFocus, Event())

# %%
