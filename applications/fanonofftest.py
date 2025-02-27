#%%

from tcspy.action.level1 import FansOn
from tcspy.action.level1 import FansOff
from tcspy.action import MultiAction
from tcspy.devices import MultiTelescopes
import schedule
import time
from multiprocessing import Event
#%%
schedule.clear()
M = MultiTelescopes()
abort_action = Event()

def fanon(multitelescope, abort_action):
    multiaction_fanon = MultiAction(
        array_telescope=multitelescope.devices.values(),
        array_kwargs={},
        function=FansOn,
        abort_action=abort_action
    )
    multiaction_fanon.run()

def fanoff(multitelescope, abort_action):
    multiaction_fanoff = MultiAction(
        array_telescope=multitelescope.devices.values(),
        array_kwargs={},
        function=FansOff,
        abort_action=abort_action
    )
    multiaction_fanoff.run()
scheduled_fanoff = schedule.every().day.at("20:50").do(fanoff, M, abort_action)
scheduled_fanoff = schedule.every().day.at("01:00").do(fanon, M, abort_action)
scheduled_fanon = schedule.every().day.at("03:00").do(fanoff, M, abort_action)
scheduled_fanoff = schedule.every().day.at("05:00").do(fanon, M, abort_action)

while schedule.get_jobs():
    schedule.run_pending()
    time.sleep(1)


# %%
