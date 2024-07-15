

#%%
from tcspy.pilot import Startup
from tcspy.pilot import NightObservation

from tcspy.devices import SingleTelescope
from tcspy.devices import MultiTelescopes
from multiprocessing import Event
from astropy.time import Time
import threading
import schedule
import time
from tcspy.pilot import BiasAcquisition, DarkAcquisition
from tcspy.pilot import Shutdown
from tcspy.utils.databases import DB
import astropy.units as u

time_now = Time.now().datetime
time_now_str = '%.2d:%.2d'%(time_now.hour, time_now.minute)
time_prepare = DB().Daily.obsnight.sunset_prepare.datetime
time_prepare_str = '%.2d:%.2d'%(time_prepare.hour-4, time_prepare.minute)
time_startobs = DB().Daily.obsnight.sunset_astro.datetime
time_startobs_str = '%.2d:%.2d'%(time_startobs.hour-4, time_startobs.minute)
time_bias = DB().Daily.obsnight.sunrise_prepare.datetime
time_dark = (Time(time_bias) + 5* u.minute).datetime
time_bias_str = '%.2d:%.2d'%(time_bias.hour-4, time_bias.minute)
time_dark_str = '%.2d:%.2d'%(time_dark.hour-4, time_dark.minute )
time_endobs = (Time(DB().Daily.obsnight.sunrise_civil.datetime) + 30 * u.minute).datetime
time_endobs_str = '%.2d:%.2d'%(time_endobs.hour-4, time_endobs.minute)
#%%

# Define a lock to synchronize the processes
process_lock = threading.Lock()
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
abort_action = Event()
M = MultiTelescopes(list_telescopes)
def run_startup():
    with process_lock:
        action_startup = Startup(M, abort_action = abort_action)
        action_startup.run()
        while action_startup.is_running:
            time.sleep(1)

def run_nightobs():
    with process_lock:
        action_nightobs = NightObservation(M, abort_action = abort_action)
        action_nightobs.run()
        while action_nightobs.is_running:
            time.sleep(1)

def run_bias():
    with process_lock:
        action_nightobs = BiasAcquisition(M, abort_action = abort_action)
        action_nightobs.run(gain = 2750)
        while action_nightobs.is_running:
            time.sleep(1)
            
def run_dark():
    with process_lock:
        action_nightobs = DarkAcquisition(M, abort_action = abort_action)
        action_nightobs.run(gain = 2750, exptime = 100)
        while action_nightobs.is_running:
            time.sleep(1)
            
def run_shutwodn():
    with process_lock:
        action_shutdown = Shutdown(M, abort_action = abort_action)
        action_shutdown.run()
        while action_shutdown.is_running:
            time.sleep(1)
    

def run_threaded(job_func):
    job_thread = threading.Thread(target=job_func)
    job_thread.start()
    
schedule.every().day.at(time_prepare_str).do(run_threaded, run_startup)
schedule.every().day.at(time_startobs_str).do(run_threaded, run_nightobs)
schedule.every().day.at(time_bias_str).do(run_threaded, run_bias)
schedule.every().day.at(time_dark_str).do(run_threaded, run_dark)
schedule.every().day.at(time_endobs_str).do(run_threaded, run_shutwodn)

while True:
    schedule.run_pending()
    time.sleep(1)
# %%
