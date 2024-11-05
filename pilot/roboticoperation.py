

#%%
from tcspy.pilot import Startup
from tcspy.pilot import NightObservation
from tcspy.utils import SlackConnector

from tcspy.devices import SingleTelescope
from tcspy.devices import MultiTelescopes
from multiprocessing import Event
from astropy.time import Time
import threading
import schedule
import time
import uuid
from tcspy.pilot import BiasAcquisition, DarkAcquisition, FlatAcquisition
from tcspy.pilot import Shutdown
from tcspy.utils.databases import DB
from tcspy.utils import NightSession
import astropy.units as u

#%%
obsnight = NightSession(Time.now()).obsnight_ltc

tonight_str = '%.4d-%.2d-%.2d'%(obsnight.sunrise_civil.datetime.year, obsnight.sunrise_civil.datetime.month, obsnight.sunrise_civil.datetime.day)

time_now = Time.now().datetime
time_now_str = '%.2d:%.2d'%(time_now.hour, time_now.minute)

# Startup
time_startup =obsnight.sunset_startup.datetime
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
print('Tonight:', tonight_str)
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
slack_schedule_str = f'Startup: {time_startup_str}\n Startobs: {time_startobs_str}\n Endobs: {time_endobs_str}\n Bias: {time_bias_str}\n Flat: {time_flat_str}\n Dark10: {time_dark10_str}\n Dark20: {time_dark20_str}\n Dark30: {time_dark30_str}\n Dark100: {time_dark100_str}\n Shutdown: {time_shutdown_str}'

#%%
# Define the telescopes
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
#%%
alert_sender = SlackConnector()
id_tonight = uuid.uuid4().hex
message_ts = alert_sender.get_message_ts(match_string = tonight_str)
if not message_ts:
    message_today = f'`7DT Observation on {tonight_str}` \n *Involving telescopes*: {", ".join(list(M.devices.keys()))} \n *Observation log*: https://hhchoi1022.notion.site/Observation-log-5af68b0822324167af57468b0852666b \n *ID*: {id_tonight}'
    alert_sender.post_message(message_today)
    time.sleep(3)
    message_ts = alert_sender.get_message_ts(match_string = tonight_str)
    alert_sender.post_thread_message(message_ts = message_ts, text = f'*Scheduled applications*: \n {slack_schedule_str}')

#%%
abort_action = Event()
# Define a lock to synchronize the processes
process_lock = threading.Lock()
#%%
def run_startup():
    with process_lock:
        start_time = time.strftime("%H:%M:%S", time.localtime())
        alert_sender.post_thread_message(message_ts = message_ts, text = f'Startup is triggered: {start_time}')
        action = Startup(M, abort_action = abort_action)
        action.run()
        while action.is_running:
            time.sleep(1)
        end_time = time.strftime("%H:%M:%S", time.localtime())
        alert_sender.post_thread_message(message_ts = message_ts, text = f'Startup is finished: {end_time}')


def run_nightobs():
    with process_lock:
        start_time = time.strftime("%H:%M:%S", time.localtime())
        alert_sender.post_thread_message(message_ts = message_ts, text = f'NightObservation is triggered: {start_time}')
        action = NightObservation(M, abort_action = abort_action)
        action.run()
        while action.is_running:
            time.sleep(1)
        end_time = time.strftime("%H:%M:%S", time.localtime())
        alert_sender.post_thread_message(message_ts = message_ts, text = f'NightObservation is finished: {end_time}')


def run_bias():
    with process_lock:
        start_time = time.strftime("%H:%M:%S", time.localtime())
        alert_sender.post_thread_message(message_ts = message_ts, text = f'BiasAcquisition is triggered: {start_time}')
        action = BiasAcquisition(M, abort_action = abort_action)
        action.run(gain = 2750)
        while action.is_running:
            time.sleep(1)
        end_time = time.strftime("%H:%M:%S", time.localtime())
        alert_sender.post_thread_message(message_ts = message_ts, text = f'BiasAcquisition is finished: {end_time}')

def run_dark10():
    with process_lock:
        start_time = time.strftime("%H:%M:%S", time.localtime())
        alert_sender.post_thread_message(message_ts = message_ts, text = f'DarkAcquisition(10s) is triggered: {start_time}')
        action = DarkAcquisition(M, abort_action = abort_action)
        action.run(gain = 2750, exptime = 10)
        while action.is_running:
            time.sleep(1)
        end_time = time.strftime("%H:%M:%S", time.localtime())
        alert_sender.post_thread_message(message_ts = message_ts, text = f'DarkAcquisition(10s) is finished: {end_time}')

def run_dark20():
    with process_lock:
        start_time = time.strftime("%H:%M:%S", time.localtime())
        alert_sender.post_thread_message(message_ts = message_ts, text = f'DarkAcquisition(20s) is triggered: {start_time}')
        action = DarkAcquisition(M, abort_action = abort_action)
        action.run(gain = 2750, exptime = 20)
        while action.is_running:
            time.sleep(1)
        end_time = time.strftime("%H:%M:%S", time.localtime())
        alert_sender.post_thread_message(message_ts = message_ts, text = f'DarkAcquisition(20s) is finished: {end_time}')

def run_dark30():
    with process_lock:
        start_time = time.strftime("%H:%M:%S", time.localtime())
        alert_sender.post_thread_message(message_ts = message_ts, text = f'DarkAcquisition(30s) is triggered: {start_time}')
        action = DarkAcquisition(M, abort_action = abort_action)
        action.run(gain = 2750, exptime = 30)
        while action.is_running:
            time.sleep(1)
        end_time = time.strftime("%H:%M:%S", time.localtime())
        alert_sender.post_thread_message(message_ts = message_ts, text = f'DarkAcquisition(30s) is finished: {end_time}')

def run_dark100():
    with process_lock:
        start_time = time.strftime("%H:%M:%S", time.localtime())
        alert_sender.post_thread_message(message_ts = message_ts, text = f'DarkAcquisition(100s) is triggered: {start_time}')
        action = DarkAcquisition(M, abort_action = abort_action)
        action.run(gain = 2750, exptime = 100)
        while action.is_running:
            time.sleep(1)
        end_time = time.strftime("%H:%M:%S", time.localtime())
        alert_sender.post_thread_message(message_ts = message_ts, text = f'DarkAcquisition(100s) is finished: {end_time}')

         
def run_flat():
    with process_lock:
        start_time = time.strftime("%H:%M:%S", time.localtime())
        alert_sender.post_thread_message(message_ts = message_ts, text = f'FlatAcquisition is triggered: {start_time}')

        action = FlatAcquisition(M, abort_action = abort_action)
        action.run(count = 9, gain = 2750, binning = 1)
        while action.is_running:
            time.sleep(1)
        end_time = time.strftime("%H:%M:%S", time.localtime())
        alert_sender.post_thread_message(message_ts = message_ts, text = f'FlatAcquisition is finished: {end_time}')
        
def run_shutdown():
    with process_lock:
        start_time = time.strftime("%H:%M:%S", time.localtime())
        alert_sender.post_thread_message(message_ts = message_ts, text = f'Shutdown is triggered: {start_time}')
        action = Shutdown(M, abort_action = abort_action)
        action.run()
        while action.is_running:
            time.sleep(1)
        end_time = time.strftime("%H:%M:%S", time.localtime())
        DB().Daily.write(clear = False)
        alert_sender.post_thread_message(message_ts = message_ts, text = f'Shutdown is finished: {end_time}')

def run_threaded(job_func):
    job_thread = threading.Thread(target=job_func)
    job_thread.start()
#%%
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
