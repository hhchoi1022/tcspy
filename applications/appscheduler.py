#%%
from tcspy.configuration import mainConfig
from tcspy.devices import SingleTelescope
from tcspy.devices import MultiTelescopes
from tcspy.utils import NightSession
from tcspy.utils import SlackConnector

from astropy.time import Time
import threading
import schedule
import json
import re

class AppScheduler(mainConfig):
    
    def __init__(self):
        super().__init__()
        self._load_multitelescopes()
        self._set_obsnight()
        self.slack_alert_sender = None
        self.slack_message_ts = None
        self.schedule = schedule
        self.thread_lock = threading.Lock()
    
    def _load_multitelescopes(self):
        print('Loading multitelescopes...')
        with open(self.config['DEVICESTATUS_FILE'],'r') as f:
            self.device_status = json.load(f)
        
        def is_telescope_active(telescope_status: dict):
            device_status = all(device['is_active'] for device in telescope_status.values())
            return device_status
        
        list_telescopes = []
        for tel_name, tel_status in self.device_status.items():
            is_tel_active = is_telescope_active(tel_status)
            tel_num = int(re.search(r"\d{2}$", tel_name).group())
            if is_tel_active:
                list_telescopes.append(SingleTelescope(tel_num))
        
        self.multitelescopes = MultiTelescopes(list_telescopes)
        print('Multitelescopes are loaded.')

    def _set_obsnight(self):
        obsnight = NightSession(Time.now()).obsnight_ltc
        self.obsnight = obsnight
        
    def _set_alert_sender(self):
        """
        Set the slack_alert_sender and slack_message_ts
        """
        tonight_str = '%.4d-%.2d-%.2d'%(self.obsnight.sunrise_civil.datetime.year, obsnight.sunrise_civil.datetime.month, self.obsnight.sunrise_civil.datetime.day)
        self.slack_alert_sender = SlackConnector()
        id_tonight = uuid.uuid4().hex
        self.slack_message_ts = alert_sender.get_message_ts(match_string = tonight_str)
        if not self.slack_message_ts:
            message_today = f'`7DT Observation on {tonight_str}` \n *Involving telescopes*: {", ".join(list(self.multitelescopes.devices.keys()))} \n *Observation log*: https://hhchoi1022.notion.site/Observation-log-5af68b0822324167af57468b0852666b \n *ID*: {id_tonight}'
            self.slack_alert_sender.post_message(message_today)
            time.sleep(3)
            self.slack_message_ts = self.slack_alert_sender.get_message_ts(match_string = tonight_str)
            #self.slack_alert_sender.post_thread_message(message_ts = self.slack_message_ts, text = f'*Scheduled applications*: \n {slack_schedule_str}')
    
    def post_slack_thread(self, message, alert_slack: bool = True):
        if alert_slack:
            if not self.slack_alert_sender:
                self._set_alert_sender()
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
            action = Startup(self.multitelescopes, abort_action = abort_action)
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
            action = NightObservation(M, abort_action = abort_action)
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
            action = BiasAcquisition(M, abort_action = abort_action)
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
            action = DarkAcquisition(M, abort_action = abort_action)
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
            action = FlatAcquisition(M, abort_action = abort_action)
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
                action = Shutdown(M, abort_action = abort_action)
                action.run(slew = slew, warm = warm)
                while action.is_running:
                    time.sleep(1)
                end_time = time.strftime("%H:%M:%S", time.localtime())
                self.post_slack_thread(message = f'Shutdown is finished: {end_time}', alert_slack = alert_slack)
  
    def show_schedule(self):
        if not self.schedule.jobs:
            print("No scheduled jobs.")
            return

        print("Current Schedule:")
        for job in self.schedule.jobs:
            next_run = job.next_run.strftime("%Y-%m-%d %H:%M:%S")
            interval = str(job).split('at')[0].strip()  # Extracting the schedule type and time
            job_func_name = job.job_func.__name__  # Get the name of the job function
            print(f"{interval} | Next run: {next_run} | Job: {job_func_name}")
            
    def schedule_app(self, application, start_time : str, *application_args):
        def run_threaded(job_func, *args):
            job_thread = threading.Thread(target=job_func, args=args)
            job_thread.start()
        self.schedule.every().day.at(start_time).do(run_threaded, application, *application_args)
    
# %%
A = AppScheduler()
# %%
