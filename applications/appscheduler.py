#%%
from tcspy.configuration import mainConfig
from tcspy.devices import SingleTelescope
from tcspy.devices import MultiTelescopes
from tcspy.utils import NightSession
from tcspy.utils.connector import SlackConnector
from tcspy.applications import BiasAcquisition
from tcspy.applications import DarkAcquisition
from tcspy.applications import NightObservation
from tcspy.applications import FilterCheck
from tcspy.applications import Startup
from tcspy.applications import Shutdown
from tcspy.applications import FlatAcquisition
from tcspy.applications import AutofocusInitializer

from ccdproc import ImageFileCollection
from threading import Event
import astropy.units as u
from astropy.time import Time
import uuid
import time
import threading
import schedule
import json
import re
import glob
import os
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
        self.tonight_str = None
        self.schedule = schedule
        self.thread_lock = threading.Lock()
        self.abort_action = abort_action

    def get_obsinfo_tonight(self, tonight_str, return_only_set : bool = True, key_for_set : list = ['exptime', 'xbinning', 'gain']):
        """
        Get all observation configurations
        """
            
        def load_collection(file_pattern, return_only_light = True):
            from astropy.table import Table, vstack
            
            # Define file search pattern
            all_files = glob.glob(file_pattern)
            if len(all_files) == 0:
                print(f"Warning: No FITS files found with pattern '{file_pattern}'")
                return None

            # Get unique parent directories
            directories = list(set(os.path.dirname(file) for file in all_files))
            
            # Initialize an empty list to store all file paths
            all_coll = Table()

            # Iterate through directories and collect FITS file paths
            for directory in directories:
                coll = ImageFileCollection(location=directory, glob_include='*.fits')
                if len(coll.files) > 0:
                    print(f"Loaded {len(coll.files)} FITS files from {directory}")

                    # Convert summary table to a uniform format
                    summary = coll.summary.copy()

                    # Ensure all string columns are explicitly converted to `str`
                    for colname in summary.colnames:
                        col_dtype = summary[colname].dtype
                        if col_dtype.kind in ('O', 'U', 'S'):  # Object, Unicode, or String types
                            summary[colname] = summary[colname].astype(str)
                        elif col_dtype.kind in ('i', 'f'):  # Integer or Float types
                            summary[colname] = summary[colname].astype(str)  # Convert to string for consistency
                            summary[colname].fill_value = ''  # Ensure NaN values are handled
                    # Stack tables
                    if all_coll is None:
                        all_coll = summary
                    else:
                        all_coll = vstack([all_coll, summary], metadata_conflicts='silent')

                else:
                    print(f"Warning: No FITS files found in {directory}")

            # Check final count of combined FITS files
            print(f"Total FITS files combined: {len(all_coll)}")
            if return_only_light:
                all_coll = all_coll[all_coll['imagetyp'] == 'LIGHT']
            return all_coll
        key = self.config['APPSCHEDULER_SEARCHKEY']
        key = key.replace("$$TONIGHT$$", tonight_str + '*')
        all_info = load_collection(key)
        if return_only_set:
            all_info_set = []
            all_info_by_config = all_info.group_by(key_for_set).groups
            for all_info_group in all_info_by_config:
                all_info_set.append(dict(exptime = all_info_group[0]['exptime'], binning = all_info_group[0]['xbinning'], gain = all_info_group[0]['gain']))
            return all_info_set
        return all_info
    
    def _set_obsnight(self):
        obsnight = NightSession(Time.now())
        self.obsnight = obsnight.obsnight_ltc
        self.obsnight_utc= obsnight.obsnight_utc
        
    def set_alert_sender(self, post_tonight_info : bool = True):
        """
        Set the slack_alert_sender and slack_message_ts
        """
        self.tonight_str = '%.4d-%.2d-%.2d'%(self.obsnight.sunrise_civil.datetime.year, self.obsnight.sunrise_civil.datetime.month, self.obsnight.sunrise_civil.datetime.day)
        self.slack_alert_sender = SlackConnector(token_path = self.config['SLACK_TOKEN'], default_channel_id = self.config['SLACK_DEFAULT_CHANNEL'])
        id_tonight = uuid.uuid4().hex
        self.slack_message_ts = self.slack_alert_sender.get_message_ts(match_string = f'7DT Observation on {self.tonight_str}')
        if not self.slack_message_ts:
            message_today = f'`7DT Observation on {self.tonight_str}` \n *Involving telescopes*: {", ".join(list(self.multitelescopes.devices.keys()))} \n *Observation log*: https://hhchoi1022.notion.site/Observation-log-5af68b0822324167af57468b0852666b \n *ID*: {id_tonight}'
            result = self.slack_alert_sender.post_message(message_today)
            self.slack_message_ts = result['ts']

            if post_tonight_info:
                # Obsnight information
                obsnight_info_str = "*Tonight information*\n" + "```" +str(self.obsnight).split('Attributes:\n')[1].split('time_inputted')[0] + "```"
                self.post_slack_thread(message = obsnight_info_str, alert_slack = alert_slack)
                time.sleep(3)

    def post_schedule(self, subject : str = '*Scheduled TCSpy applications*'):
        if self.schedule.jobs:
            schedule_str = subject + '\n'
            contents = '' 
            for job in self.schedule.jobs:
                next_run = job.next_run.strftime("%Y-%m-%d %H:%M:%S")
                job_str = str(job)
                func_match = re.search(r"do=(\w+)", job_str)
                function_name = func_match.group(1) if func_match else "Unknown"
                # Extract kwargs using regex
                kwargs_match = re.search(r"kwargs=({.*?})", job_str)
                kwargs = kwargs_match.group(1) if kwargs_match else "{}"
                contents += f"{function_name}: {next_run} \nKwargs: {kwargs}\n\n"
            contents = f"```{contents}```"
            self.post_slack_thread(message = schedule_str+contents, alert_slack = True)
    
    def post_slack_thread(self, message, alert_slack: bool = True):
        if alert_slack:
            if not self.slack_alert_sender:
                self.set_alert_sender()
            self.slack_alert_sender.post_thread_message(message_ts = self.slack_message_ts, text = message)
        else:
            return 

    def run_filtercheck(self,
                        exptime = 60,
                        alert_slack : bool = True):
        with self.thread_lock:
            start_time = time.strftime("%H:%M:%S", time.localtime())
            self.post_slack_thread(message = f'Filtercheck is triggered: {start_time}', alert_slack = alert_slack)
            action = FilterCheck(self.multitelescopes, abort_action = self.abort_action)
            result = action.run(exptime = exptime)
            while action.is_running:
                time.sleep(1)
            end_time = time.strftime("%H:%M:%S", time.localtime())
            self.post_slack_thread(message = f'Filtercheck is finished: {end_time}', alert_slack = alert_slack)
            # Convert result[0] dictionary to a formatted string
            skylevel_str = '\n'.join([f'{band}: ' + ', '.join([f'{telescope}: {value} \n' for telescope, value in telescopes.items()])
                                    for band, telescopes in result[0].items()])
            self.post_slack_thread(message=f'Skylevel:\n{skylevel_str}', alert_slack=alert_slack)
            return self.schedule.CancelJob  # Remove this job after execution
 
    def run_autofocus_init(self,
                           filter_ = 'specall',
                           use_history = True,
                           history_duration = 0,
                           search_focus_when_failed = True,
                           search_focus_range = 3000,
                           slew = True,
                           alert_slack : bool = True):
        with self.thread_lock:
            start_time = time.strftime("%H:%M:%S", time.localtime())
            self.post_slack_thread(message = f'Autofocus_initialization is triggered: {start_time}', alert_slack = alert_slack)
            action = AutofocusInitializer(self.multitelescopes, abort_action = self.abort_action)
            result = action.run(filter_ = filter_,
                                use_history = use_history, 
                                history_duration = history_duration,
                                search_focus_when_failed = search_focus_when_failed, 
                                search_focus_range = search_focus_range,
                                slew = slew) 
            while action.is_running:
                time.sleep(1)
            end_time = time.strftime("%H:%M:%S", time.localtime())
            self.post_slack_thread(message = f'Autofocus_initialization is finished: {end_time}', alert_slack = alert_slack)
            # Convert result[0] dictionary to a formatted string
            return self.schedule.CancelJob  # Remove this job after execution
 
 
    def run_startup(self,
                    connect = True,
                    home = True,
                    slew = True,
                    cool = True,
                    alert_slack : bool = True):
        with self.thread_lock:
            start_time = time.strftime("%H:%M:%S", time.localtime())
            self.post_slack_thread(message = f'StartUp is triggered: {start_time}', alert_slack = alert_slack)
            action = Startup(self.multitelescopes, abort_action = self.abort_action)
            action.run(connect = connect, home = home, slew = slew, cool = cool)
            while action.is_running:
                time.sleep(1)
            end_time = time.strftime("%H:%M:%S", time.localtime())
            self.post_slack_thread(message = f'StartUp is finished: {end_time}', alert_slack = alert_slack)
            return self.schedule.CancelJob  # Remove this job after execution
 
    def run_nightobs(self,
                     alert_slack : bool = True):
        with self.thread_lock:
            from tcspy.utils.databases import DB
            start_time = time.strftime("%H:%M:%S", time.localtime())
            self.post_slack_thread(message = f'NightObservation is triggered: {start_time}', alert_slack = alert_slack)
            action = NightObservation(self.multitelescopes, abort_action = self.abort_action)
            action.run()
            while action.is_running:
                time.sleep(1)
            end_time = time.strftime("%H:%M:%S", time.localtime())
            self.post_slack_thread(message = f'NightObservation is finished: {end_time}', alert_slack = alert_slack)
            DB().Dynamic.export_to_csv(save_type= 'history')
            return self.schedule.CancelJob  # Remove this job after execution

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
            return self.schedule.CancelJob  # Remove this job after execution
    
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
            return self.schedule.CancelJob  # Remove this job after execution

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
            return self.schedule.CancelJob  # Remove this job after execution
    
    def run_shutdown(self,
                     fanoff : bool = True,
                     slew : bool = True,
                     warm : bool = True,
                     alert_slack : bool = True):
        with self.thread_lock:
            start_time = time.strftime("%H:%M:%S", time.localtime())
            self.post_slack_thread(message = f'Shutdown is triggered: {start_time}', alert_slack = alert_slack)
            action = Shutdown(self.multitelescopes, abort_action = self.abort_action)
            action.run(fanoff = fanoff, slew = slew, warm = warm)
            while action.is_running:
                time.sleep(1)
            end_time = time.strftime("%H:%M:%S", time.localtime())
            self.post_slack_thread(message = f'Shutdown is finished: {end_time}', alert_slack = alert_slack)
            return self.schedule.CancelJob  # Remove this job after execution
  
    def show_schedule(self,
                      alert_slack : bool = True):
        if not self.schedule.jobs:
            print("No scheduled jobs.")
            return

        print("Current Schedule:")
        for job in self.schedule.jobs:
            next_run = job.next_run.strftime("%Y-%m-%d %H:%M:%S")
            job_str = str(job)
            func_match = re.search(r"do=(\w+)", job_str)
            function_name = func_match.group(1) if func_match else "Unknown"
            # Extract kwargs using regex
            kwargs_match = re.search(r"kwargs=({.*?})", job_str)
            kwargs = kwargs_match.group(1) if kwargs_match else "{}"
            print(f"{function_name} | Next run: {next_run} | Job: {function_name} | kwargs: {kwargs}")

    def clear_schedule(self):
        self.schedule.clear()
             
    def schedule_app(self, application, start_time : Time, **application_kwargs):
        start_time_str = '%.2d:%.2d'%(start_time.datetime.hour, start_time.datetime.minute)
        self.schedule.every().day.at(start_time_str).do(application, **application_kwargs)

    def run_schedule(self):
        while self.schedule.get_jobs():
            self.schedule.run_pending()
            time.sleep(1)
            
    def dummpy_run(self):
        print('Dummy run')
        return self.schedule.CancelJob
            

# %%
if __name__ == '__main__':
    M = MultiTelescopes()
    abort_action = Event()
    A = AppScheduler(M, abort_action)
    A.clear_schedule()
    alert_slack = True

    # # Startup
    if Time.now() < A.obsnight_utc.sunset_startup:
        A.schedule_app(A.run_startup, A.obsnight.sunset_startup, connect = True, home = True, slew = True, cool = True, alert_slack = alert_slack)
    # Filtercheck
    if Time.now() < A.obsnight_utc.sunset_flat:
        A.schedule_app(A.run_filtercheck, A.obsnight.sunset_flat, exptime = 60)
    # Autofocus_init
    autofocus_start_time = A.obsnight.sunset_flat + 15*u.minute
    if Time.now() < autofocus_start_time:
        A.schedule_app(A.run_autofocus_init, autofocus_start_time, 
                       filter_ = 'specall',
                       use_history = True,
                       history_duration = 0,
                       search_focus_when_failed = True,
                       search_focus_range = 3000,
                       slew = True,
                       alert_slack = True)
        autofocus_start_time += 10*u.minute
        A.schedule_app(A.run_autofocus_init, autofocus_start_time,
                       filter_ = 'specall',
                       use_history = True,
                       history_duration = 0,
                       search_focus_when_failed = True,
                       search_focus_range = 3000,
                       slew = True,
                       alert_slack = True)
    # NightObservation
    if Time.now() < A.obsnight_utc.sunset_observation:
        A.schedule_app(A.run_nightobs, A.obsnight.sunset_observation, alert_slack = alert_slack)

    A.set_alert_sender(post_tonight_info= True)
    A.post_schedule(subject = '*Scheduled TCSpy apploication before nightly observation*')
    A.show_schedule()

    if A.schedule.jobs:
        A.run_schedule()
        time.sleep(10)
        A.clear_schedule()


    while Time.now() < A.obsnight_utc.sunrise_observation + 5 * u.minute:
        time.sleep(1)
    
    # Flat
    if Time.now() < A.obsnight_utc.sunrise_flat:
        A.schedule_app(A.run_flat, A.obsnight.sunrise_flat, count = 9, binning = 1, gain = 2750, alert_slack = alert_slack)

    # Dark
    utcdate12 = (A.obsnight.sunset_observation - 12 * u.hour).datetime
    tonight_str = '%.4d-%.2d-%.2d'%(utcdate12.year, utcdate12.month, utcdate12.day)
    all_obsinfo = A.get_obsinfo_tonight(tonight_str, return_only_set= True, key_for_set = ['exptime', 'xbinning', 'gain'])
    dark_count = 9
    dark_starttime = A.obsnight.sunrise_shutdown + 10 * u.minute
    dark_starttime_utc = A.obsnight_utc.sunrise_shutdown + 10 * u.minute
    if Time.now() < dark_starttime_utc:
        for obsinfo in all_obsinfo:
            exptected_duration = float(obsinfo['exptime']) * dark_count * 1.3
            A.schedule_app(A.run_dark, dark_starttime, count = int(dark_count), exptime = float(obsinfo['exptime']), binning = int(obsinfo['binning']), gain = int(obsinfo['gain']), alert_slack = alert_slack)
            dark_starttime += exptected_duration * u.second

    # Bias
    all_obsinfo = A.get_obsinfo_tonight(tonight_str, return_only_set= True, key_for_set= ['xbinning', 'gain'])
    bias_count = 9
    bias_starttime = dark_starttime + 15 * u.minute
    bias_starttime_utc = dark_starttime_utc + 10 * u.minute
    if Time.now() < bias_starttime_utc:
        for obsinfo in all_obsinfo:
            A.schedule_app(A.run_bias, bias_starttime, count = int(bias_count), binning = int(obsinfo['binning']), gain = int(obsinfo['gain']), alert_slack = alert_slack)
            bias_starttime += 10 * u.minute

    # Shutdown
    shutdown_starttime = bias_starttime + 20 * u.minute
    shutdown_starttime_utc = bias_starttime_utc + 10 * u.minute
    if Time.now() < shutdown_starttime_utc:
        A.schedule_app(A.run_shutdown, shutdown_starttime, fanoff = True, slew = True, warm = True, alert_slack = alert_slack)

    A.post_schedule(subject = '*Scheduled TCSpy apploication after nightly observation*')
    A.show_schedule()
    A.run_schedule()

# %%
