#%%
from tcspy.action.level2 import AutoFocus
from tcspy.action import MultiAction
from tcspy.action.level1 import SlewAltAz
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
alt = 50
az = 0
tracking= True
action_slew = MultiAction(list_telescopes, dict(alt = alt, az = az, tracking = tracking), SlewAltAz, Event())