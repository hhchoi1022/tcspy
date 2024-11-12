#%%
from tcspy.configuration import mainConfig
from tcspy.devices import SingleTelescope
from tcspy.devices import MultiTelescopes

import threading
import schedule
import json
import re

class AppScheduler(mainConfig):
    
    def __init__(self):
        super().__init__()
        self._load_multitelescopes()
        self.schedule = schedule
        self.thread_lock = threading.Lock()
    
    def _load_multitelescopes(self):
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
    
    def run_startup(self,
                    home = True,
                    slew = True,
                    cool = True):
        with self.thread_lock:
            action = Startup(self.multitelescopes, abort_action = abort_action)
            action.run(home = home, slew = slew, cool = cool)
            while action.is_running:
                time.sleep(1)
        
    
                
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
a = AppScheduler()
# %%
# %%
