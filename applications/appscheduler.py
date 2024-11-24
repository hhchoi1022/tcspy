#%%
from tcspy.configuration import mainConfig
from tcspy.devices import SingleTelescope
from tcspy.devices import MultiTelescopes
from tcspy.utils import NightSession
from tcspy.utils import SlackConnector
from tcspy.applications import BiasAcquisition
from tcspy.applications import DarkAcquisition
from tcspy.applications import NightObservation
from tcspy.applications import Startup
from tcspy.applications import Shutdown
from tcspy.applications import FlatAcquisition

from threading import Event
import astropy.units as u
from astropy.time import Time
import uuid
import time
import threading
import schedule
import json
import re
#%%
class AppScheduler(mainConfig):
    
    def __init__(self,
                 multitelescopes : MultiTelescopes,
                 abort_action : Event,
                 ):
        super().__init__()
        self.multitelescopes = multitelescopes
        self._set_obsnight()
        self.slack_alert_sender = None
        self.slack_message_ts = None
        self.schedule = schedule
        self.thread_lock = threading.Lock()
        self.abort_action = abort_action

    def _set_obsnight(self):
        obsnight = NightSession(Time.now()).obsnight_ltc
        self.obsnight = obsnight
        
    def set_alert_sender(self, post_schedule : bool = True):
        """
        Set the slack_alert_sender and slack_message_ts
        """
        tonight_str = '%.4d-%.2d-%.2d'%(self.obsnight.sunrise_civil.datetime.year, self.obsnight.sunrise_civil.datetime.month, self.obsnight.sunrise_civil.datetime.day)
        self.slack_alert_sender = SlackConnector()
        id_tonight = uuid.uuid4().hex
        self.slack_message_ts = self.slack_alert_sender.get_message_ts(match_string = tonight_str)
        if not self.slack_message_ts:
            message_today = f'`7DT Observation on {tonight_str}` \n *Involving telescopes*: {", ".join(list(self.multitelescopes.devices.keys()))} \n *Observation log*: https://hhchoi1022.notion.site/Observation-log-5af68b0822324167af57468b0852666b \n *ID*: {id_tonight}'
            self.slack_alert_sender.post_message(message_today)
            time.sleep(3)
            self.slack_message_ts = self.slack_alert_sender.get_message_ts(match_string = tonight_str)

            if post_schedule:
                # Obsnight information
                obsnight_info_str = "*Tonight information*\n" +str(self.obsnight).split('Attributes:\n')[1].split('time_inputted')[0]
                self.post_slack_thread(message = obsnight_info_str, alert_slack = alert_slack)
                time.sleep(3)
                if self.schedule.jobs:
                    schedule_str = '*Tonight scheduled TCSpy applications*\n' 
                    for job in self.schedule.jobs:
                        next_run = job.next_run.strftime("%Y-%m-%d %H:%M:%S")
                        job_str = str(job)
                        func_match = re.search(r"<bound method .*?\.([\w_]+) of", job_str)
                        function_name = func_match.group(1) if func_match else "Unknown"
                        # Extract kwargs using regex
                        kwargs_match = re.search(r"kwargs=({.*?})", job_str)
                        kwargs = kwargs_match.group(1) if kwargs_match else "{}"
                        schedule_str += f"`{function_name}`: {next_run} \nKwargs: {kwargs}\n\n"
                    self.post_slack_thread(message = schedule_str, alert_slack = alert_slack)
            
    
    def post_slack_thread(self, message, alert_slack: bool = True):
        if alert_slack:
            if not self.slack_alert_sender:
                self.set_alert_sender()
            self.slack_alert_sender.post_thread_message(message_ts = self.slack_message_ts, text = message)
        else:
            return 
        
    def run_startup(self,
                    home = True,
                    slew = True,
                    cool = True,
                    alert_slack : bool = True):
        with self.thread_lock:
            start_time = time.strftime("%H:%M:%S", time.localtime())
            self.post_slack_thread(message = f'StartUp is triggered: {start_time}', alert_slack = alert_slack)
            action = Startup(self.multitelescopes, abort_action = self.abort_action)
            action.run(home = home, slew = slew, cool = cool)
            while action.is_running:
                time.sleep(1)
            end_time = time.strftime("%H:%M:%S", time.localtime())
            self.post_slack_thread(message = f'StartUp is finished: {end_time}', alert_slack = alert_slack)
                    
    def run_nightobs(self,
                     alert_slack : bool = True):
        with self.thread_lock:
            start_time = time.strftime("%H:%M:%S", time.localtime())
            self.post_slack_thread(message = f'NightObservation is triggered: {start_time}', alert_slack = alert_slack)
            action = NightObservation(self.multitelescopes, abort_action = self.abort_action)
            action.run()
            while action.is_running:
                time.sleep(1)
            end_time = time.strftime("%H:%M:%S", time.localtime())
            self.post_slack_thread(message = f'NightObservation is finished: {end_time}', alert_slack = alert_slack)
    
    def run_bias(self,
                 count : int = 9,
                 binning : int = 1,
                 gain : int = 2750,
                 alert_slack : bool = True):
        with self.thread_lock:
            start_time = time.strftime("%H:%M:%S", time.localtime())
            self.post_slack_thread(message = f'BiasAcquisition is triggered: {start_time}', alert_slack = alert_slack)
            action = BiasAcquisition(self.multitelescopes, abort_action = self.abort_action)
            action.run(count = count, binning = binning, gain = gain)
            while action.is_running:
                time.sleep(1)
            end_time = time.strftime("%H:%M:%S", time.localtime())
            self.post_slack_thread(message = f'BiasAcquisition is finished: {end_time}', alert_slack = alert_slack)
    
    def run_dark(self,
                 count : int = 9,
                 exptime : int = 100,
                 binning : int = 1,
                 gain : int = 2750,
                 alert_slack : bool = True):
        with self.thread_lock:
            start_time = time.strftime("%H:%M:%S", time.localtime())
            self.post_slack_thread(message = f'DarkAcquisition is triggered: {start_time}', alert_slack = alert_slack)
            action = DarkAcquisition(self.multitelescopes, abort_action = self.abort_action)
            action.run(count = count, exptime = exptime, binning = binning, gain = gain)
            while action.is_running:
                time.sleep(1)
            end_time = time.strftime("%H:%M:%S", time.localtime())
            self.post_slack_thread(message = f'DarkAcquisition is finished: {end_time}', alert_slack = alert_slack)

    def run_flat(self,
                 count : int = 9,
                 binning : int = 1,
                 gain : int = 2750,
                 alert_slack : bool = True):
        with self.thread_lock:
            start_time = time.strftime("%H:%M:%S", time.localtime())
            self.post_slack_thread(message = f'FlatAcquisition is triggered: {start_time}', alert_slack = alert_slack)
            action = FlatAcquisition(self.multitelescopes, abort_action = self.abort_action)
            action.run(count = count, binning = binning, gain = gain)
            while action.is_running:
                time.sleep(1)
            end_time = time.strftime("%H:%M:%S", time.localtime())
            self.post_slack_thread(message = f'FlatAcquisition is finished: {end_time}', alert_slack = alert_slack)

    def run_shutdown(self,
                     slew : bool = True,
                     warm : bool = True,
                     alert_slack : bool = True):
            with self.thread_lock:
                start_time = time.strftime("%H:%M:%S", time.localtime())
                self.post_slack_thread(message = f'Shutdown is triggered: {start_time}', alert_slack = alert_slack)
                action = Shutdown(self.multitelescopes, abort_action = self.abort_action)
                action.run(slew = slew, warm = warm)
                while action.is_running:
                    time.sleep(1)
                end_time = time.strftime("%H:%M:%S", time.localtime())
                self.post_slack_thread(message = f'Shutdown is finished: {end_time}', alert_slack = alert_slack)
  
    def show_schedule(self,
                      alert_slack : bool = True):
        if not self.schedule.jobs:
            print("No scheduled jobs.")
            return

        print("Current Schedule:")
        for job in self.schedule.jobs:
            next_run = job.next_run.strftime("%Y-%m-%d %H:%M:%S")
            job_str = str(job)
            func_match = re.search(r"<bound method .*?\.([\w_]+) of", job_str)
            function_name = func_match.group(1) if func_match else "Unknown"
            # Extract kwargs using regex
            kwargs_match = re.search(r"kwargs=({.*?})", job_str)
            kwargs = kwargs_match.group(1) if kwargs_match else "{}"
            print(f"{function_name} | Next run: {next_run} | Job: {function_name} | kwargs: {kwargs}")

    def clear_schedule(self):
        self.schedule.clear()
             
    def schedule_app(self, application, start_time : Time, **application_kwargs):
        def run_threaded(job_func, **kwargs):
            job_thread = threading.Thread(target=job_func, kwargs=kwargs)
            job_thread.start()
        start_time_str = '%.2d:%.2d'%(start_time.datetime.hour, start_time.datetime.minute)
        self.schedule.every().day.at(start_time_str).do(run_threaded, application, **application_kwargs)

    def run_schedule(self):
        while True:
            self.schedule.run_pending()
            time.sleep(1)
# %%
if __name__ == '__main__':
    M = MultiTelescopes()
    abort_action = Event()
    A = AppScheduler(M, abort_action)
    A.clear_schedule()
    alert_slack = True
    # Startup
    A.schedule_app(A.run_startup, A.obsnight.sunset_startup, home = True, slew = True, cool = True, alert_slack = alert_slack)
    # NightObservation
    A.schedule_app(A.run_nightobs, A.obsnight.sunset_observation, alert_slack = alert_slack)
    # Bias
    A.schedule_app(A.run_bias, A.obsnight.sunrise_observation + 15 * u.minute, count = 9, binning = 1, gain = 2750, alert_slack = alert_slack)
    # Flat
    A.schedule_app(A.run_flat, A.obsnight.sunrise_flat, count = 9, binning = 1, gain = 2750, alert_slack = alert_slack)
    # Dark
    A.schedule_app(A.run_dark, A.obsnight.sunrise_flat + 40 * u.minute, count = 9, exptime = 100, binning = 1, gain = 2750, alert_slack = alert_slack)
    # Shutdown
    A.schedule_app(A.run_shutdown, A.obsnight.sunrise_flat + 1 * u.hour, slew = True, warm = True, alert_slack = alert_slack)
    A.set_alert_sender(post_schedule= True)
    A.show_schedule()
    A.run_schedule()
# %%
