

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
from tcspy.utils import NightSession
import astropy.units as u
#%%
obsnight = NightSession(Time.now()).obsnight

time_now = Time.now().datetime
time_now_str = '%.2d:%.2d'%(time_now.hour, time_now.minute)

# Startup
time_startup =obsnight.sunset_prepare.datetime
time_startup_str = '%.2d:%.2d'%(time_startup.hour-4, time_startup.minute)

# Observation start 
time_startobs =obsnight.sunset_astro.datetime
time_startobs_str = '%.2d:%.2d'%(time_startobs.hour-4, time_startobs.minute)

# BIAS
time_bias =obsnight.sunrise_prepare.datetime
time_bias_str = '%.2d:%.2d'%(time_bias.hour-4, time_bias.minute)

# DARK
time_dark = (Time(time_bias) + 5* u.minute).datetime
time_dark_str = '%.2d:%.2d'%(time_dark.hour-4, time_dark.minute )

# FLAT
time_flat = obsnight.sunrise_flat.datetime
time_flat_str = '%.2d:%.2d'%(time_flat.hour-4, time_flat.minute )

# Shutdown
time_shutdown = (Time(obsnight.sunrise_civil.datetime) + 30 * u.minute).datetime
time_shutdown_str = '%.2d:%.2d'%(time_shutdown.hour-4, time_shutdown.minute)

#%%
# Define the telescopes
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
M = MultiTelescopes(list_telescopes)

abort_action = Event()
# Define a lock to synchronize the processes
process_lock = threading.Lock()

def run_startup():
    with process_lock:
        action = Startup(M, abort_action = abort_action)
        action.run()
        while action_startup.is_running:
            time.sleep(1)

def run_nightobs():
    with process_lock:
        action = NightObservation(M, abort_action = abort_action)
        action.run()
        while action_nightobs.is_running:
            time.sleep(1)

def run_bias():
    with process_lock:
        action = BiasAcquisition(M, abort_action = abort_action)
        action.run(gain = 2750)
        while action_nightobs.is_running:
            time.sleep(1)
            
def run_dark():
    with process_lock:
        action = DarkAcquisition(M, abort_action = abort_action)
        action.run(gain = 2750, exptime = 100)
        while action_nightobs.is_running:
            time.sleep(1)

def run_flat():
    with process_lock:
        action = FlatAcquisition(M, abort_action = abort_action)
        action.run(count = 9, gain = 2750, binning = 1)
        while action_nightobs.is_running:
            time.sleep(1)
            
def run_shutdown():
    with process_lock:
        action = Shutdown(M, abort_action = abort_action)
        action.run()
        while action_shutdown.is_running:
            time.sleep(1)

def run_threaded(job_func):
    job_thread = threading.Thread(target=job_func)
    job_thread.start()
    
schedule.every().day.at(time_startup_str).do(run_threaded, run_startup)
schedule.every().day.at(time_startobs_str).do(run_threaded, run_nightobs)
schedule.every().day.at(time_bias_str).do(run_threaded, run_bias)
schedule.every().day.at(time_dark_str).do(run_threaded, run_dark)
schedule.every().day.at(time_flat_str).do(run_threaded, run_flat)
schedule.every().day.at(time_shutdown_str).do(run_threaded, run_shutdown)

while True:
    schedule.run_pending()
    time.sleep(1)
# %%
