

#%%
from tcspy.applications import Startup
from tcspy.applications import NightObservation

from tcspy.devices import SingleTelescope
from tcspy.devices import MultiTelescopes
from multiprocessing import Event
from astropy.time import Time
import threading
import schedule
import time
from tcspy.applications import BiasAcquisition, DarkAcquisition, FlatAcquisition
from tcspy.applications import Shutdown
from tcspy.utils.databases import DB
from tcspy.utils import NightSession
import astropy.units as u

#%%
obsnight = NightSession(Time.now()).obsnight_ltc

time_now = Time.now().datetime
time_now_str = '%.2d:%.2d'%(time_now.hour, time_now.minute)

# Startup
time_startup =obsnight.sunset_prepare.datetime
time_startup_str = '%.2d:%.2d'%(time_startup.hour, time_startup.minute)

# Observation start 
time_startobs =obsnight.sunset_observation.datetime
time_startobs_str = '%.2d:%.2d'%(time_startobs.hour, time_startobs.minute)

# Observation start 
time_endobs =obsnight.sunrise_observation.datetime
time_endobs_str = '%.2d:%.2d'%(time_endobs.hour, time_endobs.minute)

# BIAS
time_bias = (obsnight.sunrise_observation + 15 * u.minute).datetime 
time_bias_str = '%.2d:%.2d'%(time_bias.hour, time_bias.minute)

# FLAT
time_flat = (obsnight.sunrise_flat).datetime
#time_flat = obsnight.sunrise_flat.datetime
time_flat_str = '%.2d:%.2d'%(time_flat.hour, time_flat.minute )

# DARK10
time_dark10 = (obsnight.sunrise_flat + 40 * u.minute).datetime
time_dark10_str = '%.2d:%.2d'%(time_dark10.hour, time_dark10.minute )
# DARK20
time_dark20 = (obsnight.sunrise_flat + 45 * u.minute).datetime
time_dark20_str = '%.2d:%.2d'%(time_dark20.hour, time_dark20.minute )
# DARK30
time_dark30 = (obsnight.sunrise_flat +  55* u.minute).datetime
time_dark30_str = '%.2d:%.2d'%(time_dark30.hour, time_dark30.minute )
# DARK100
time_dark100 = (obsnight.sunrise_flat + 70 * u.minute).datetime
time_dark100_str = '%.2d:%.2d'%(time_dark100.hour, time_dark100.minute )

# Shutdown
time_shutdown = (Time(time_dark100) + 30 * u.minute).datetime
time_shutdown_str = '%.2d:%.2d'%(time_shutdown.hour, time_shutdown.minute)
print('The schedule is:')   
print('Startup:', time_startup_str)
print('Startobs:', time_startobs_str)
print('Endobs:', time_endobs_str)
print('Bias:', time_bias_str)
print('Flat:', time_flat_str)

print('Dark10:', time_dark10_str)
print('Dark20:', time_dark20_str)
print('Dark30:', time_dark30_str)
print('Dark100:', time_dark100_str)
print('Shutdown:', time_shutdown_str)
#%%
# Define the telescopes
list_telescopes = [#SingleTelescope(1),
                    SingleTelescope(2),
                    SingleTelescope(3),
                    SingleTelescope(5),
                    SingleTelescope(6),
                    SingleTelescope(7),
                    SingleTelescope(8),
                    SingleTelescope(9),
                    #SingleTelescope(10),
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
        while action.is_running:
            time.sleep(1)

def run_nightobs():
    with process_lock:
        action = NightObservation(M, abort_action = abort_action)
        action.run()
        while action.is_running:
            time.sleep(1)

def run_bias():
    with process_lock:
        action = BiasAcquisition(M, abort_action = abort_action)
        action.run(gain = 0)
        while action.is_running:
            time.sleep(1)
            
def run_dark10():
    with process_lock:
        action = DarkAcquisition(M, abort_action = abort_action)
        action.run(gain = 0, exptime = 10)
        while action.is_running:
            time.sleep(1)
def run_dark20():
    with process_lock:
        action = DarkAcquisition(M, abort_action = abort_action)
        action.run(gain = 0, exptime = 20)
        while action.is_running:
            time.sleep(1)
def run_dark30():
    with process_lock:
        action = DarkAcquisition(M, abort_action = abort_action)
        action.run(gain = 0, exptime = 30)
        while action.is_running:
            time.sleep(1)
def run_dark100():
    with process_lock:
        action = DarkAcquisition(M, abort_action = abort_action)
        action.run(gain = 0, exptime = 100)
        while action.is_running:
            time.sleep(1)
            
def run_flat():
    with process_lock:
        action = FlatAcquisition(M, abort_action = abort_action)
        action.run(count = 9, gain = 0, binning = 1)
        while action.is_running:
            time.sleep(1)
            
def run_shutdown():
    with process_lock:
        action = Shutdown(M, abort_action = abort_action)
        action.run()
        while action.is_running:
            time.sleep(1)

def run_threaded(job_func):
    job_thread = threading.Thread(target=job_func)
    job_thread.start()
    
schedule.every().day.at(time_startup_str).do(run_threaded, run_startup)
schedule.every().day.at(time_startobs_str).do(run_threaded, run_nightobs)
schedule.every().day.at(time_bias_str).do(run_threaded, run_bias)
schedule.every().day.at(time_dark10_str).do(run_threaded, run_dark10)
schedule.every().day.at(time_dark20_str).do(run_threaded, run_dark20)
schedule.every().day.at(time_dark30_str).do(run_threaded, run_dark30)
schedule.every().day.at(time_dark100_str).do(run_threaded, run_dark100)
schedule.every().day.at(time_flat_str).do(run_threaded, run_flat)
schedule.every().day.at(time_shutdown_str).do(run_threaded, run_shutdown)

while True:
    schedule.run_pending()
    time.sleep(1)
# %%
