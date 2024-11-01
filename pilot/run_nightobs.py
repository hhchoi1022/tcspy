#%%
from tcspy.pilot import NightObservation
from tcspy.devices import SingleTelescope
from tcspy.devices import MultiTelescopes
from threading import Event, Thread

list_telescopes = [#SingleTelescope(1),
                        SingleTelescope(2),
                        SingleTelescope(3),
                        SingleTelescope(4),
                        SingleTelescope(5),
                        #SingleTelescope(6),
                        SingleTelescope(7),
                        SingleTelescope(8),
                        SingleTelescope(9),
                        SingleTelescope(10),
                        SingleTelescope(11),
                        SingleTelescope(13),
                        SingleTelescope(14)
                        ]
M = MultiTelescopes(list_telescopes)
abort_action = Event()
R = NightObservation(M, abort_action= abort_action)
R.run()
# %%

