


#%%
from astropy.time import Time
from threading import Event, Lock
from threading import Thread
from queue import Queue
import time
import uuid

from tcspy.action.level1 import *
from tcspy.action.level2 import *
from tcspy.action.level3 import *
from tcspy.action import MultiAction
from tcspy.configuration import mainConfig
from tcspy.devices import MultiTelescopes
from tcspy.devices import SingleTelescope
from tcspy.utils.databases import DB
from tcspy.devices.weather import WeatherUpdater
from tcspy.utils.error import *

#%%


class NightObservation(mainConfig):
    
    def __init__(self, 
                 MultiTelescopes : MultiTelescopes,
                 abort_action : Event,
                 ):
        super().__init__()
        self.multitelescopes = MultiTelescopes
        self.abort_action = abort_action
        self.DB = self._update_DB(utctime = Time.now())
        self.action_queue = list()
        self.tel_queue = dict()
        self.initialize()
        self.tel_lock = Lock()
        self.action_lock = Lock()

        self._observation_abort = Event()
    
    def initialize(self):
        
        # Initialize Daily target table 
        self.DB = DB(utctime = Time.now()).Daily
        self.DB.initialize(initialize_all= False)
        if all(Time(self.DB.data['settime']) < Time.now()):
            self.DB.initialize(initialize_all= True)
        is_connected_DB = self.DB.connected
        
        if not is_connected_DB:
            raise DBConnectionError('DB cannot be connected. Check MySQL server')
        
        # Connect Weather Updater
        self.WEATHER = WeatherUpdater()
        Thread(target = self.WEATHER.run, kwargs = dict(abort_action = self.abort_action), daemon = True).start()
        
        # Get status of all telescopes
        status_devices = self.multitelescopes.status
        for tel_name, status in status_devices.items():
            if self._tel_is_ready(status):
                self.tel_queue[tel_name] = self.multitelescopes.devices[tel_name]
        
        # Set observing night
        self.obsnight = self.DB.obsnight
        
        # Initialization is finished

    def _tel_is_ready(self, tel_status_dict):
        ready_tel = tel_status_dict['mount'].upper() == 'IDLE'
        ready_cam = tel_status_dict['camera'].upper() == 'IDLE'
        ready_filt = tel_status_dict['filterwheel'].upper() == 'IDLE'
        ready_focus = tel_status_dict['focuser'].upper() == 'IDLE'
        return all([ready_tel, ready_cam, ready_filt, ready_focus])
    
    def _obstrigger(self, target, abort_action):
        
        def _specobs(target, multitelescopes, abort_action):
            kwargs = dict(exptime = target['exptime'], 
                        count = target['count'],
                        specmode = target['specmode'],
                        binning = target['binning'], 
                        imgtype = 'Light', 
                        ra = target['RA'],
                        dec = target['De'], 
                        name = target['objname'],
                        objtype = target['objtype'], 
                        autofocus_before_start = True,
                        autofocus_when_filterchange= True)        
            self.DB.Daily.update_target(update_value = 'scheduled', update_key = 'status', id_value = target['id'], id_key = 'id')
            action = SpecObservation(multitelescopes= multitelescopes, abort_action = abort_action)
            action_id = uuid.uuid4().hex
            # Pop the telescope from the tel_queue
            for tel_name, tel in multitelescopes.devices.items():
                self.pop_telescope(tel)
                #self.tel_queue.pop(tel_name, None)
            # Apped the action and telescope to the action_queue
            self.put_action(target = target, action = action, telescopes = multitelescopes, action_id = action_id)
            #self.action_queue.append({'target': target['objname'], 'action': action, 'tel' : multitelescopes, 'id' : action_id})
            
            # Run observation
            result_action = action.run(**kwargs)
            
            # Update the target status
            if result_action:
                self.DB.Daily.update_target(update_value = 'observed', update_key = 'status', id_value = target['id'], id_key = 'id')
            else:
                self.DB.Daily.update_target(update_value = 'failed', update_key = 'status', id_value = target['id'], id_key = 'id')
            # Pop the action and telescope from  the action_queue
            self.pop_action(action_id = action_id)
            #self.action_queue = [item for item in self.action_queue if item.get('id') != action_id]
            # Apped the telescope to the tel_queue
            for tel_name, tel in multitelescopes.devices.items():
                self.put_telescope(telescope = tel)
                #self.tel_queue[tel_name] = multitelescopes.devices[tel_name]
            
        def _deepobs(target, multitelescopes, abort_action):
            kwargs = dict(exptime = target['exptime'], 
                        count = target['count'],
                        filter_ = target['filter_'],
                        binning = target['binning'], 
                        imgtype = 'Light',
                        ra = target['RA'],
                        dec = target['De'], 
                        name = target['objname'],
                        objtype = target['objtype'], 
                        autofocus_before_start = True,
                        autofocus_when_filterchange= True)
            self.DB.Daily.update_target(update_value = 'scheduled', update_key = 'status', id_value = target['id'], id_key = 'id')
            action = DeepObservation(multitelescopes= multitelescopes, abort_action = abort_action)
            action_id = uuid.uuid4().hex
            # Pop the telescope from the tel_queue
            for tel_name in multitelescopes.devices.keys():
                self.tel_queue.pop(tel_name, None)
            # Apped the action and telescope to the action_queue
            self.action_queue.append({'target': target['objname'], 'action': action, 'tel' : multitelescopes, 'id' : action_id})
            
            # Run observation
            result_action = action.run(**kwargs)
            
            # Update the target status
            if result_action:
                self.DB.Daily.update_target(update_value = 'observed', update_key = 'status', id_value = target['id'], id_key = 'id')
            else:
                self.DB.Daily.update_target(update_value = 'failed', update_key = 'status', id_value = target['id'], id_key = 'id')
            # Pop the action and telescope from the action_queue
            self.action_queue = [item for item in self.action_queue if item.get('id') != action_id]
            # Apped the telescope to the tel_queue
            for tel_name in multitelescopes.devices.keys():
                self.tel_queue[tel_name] = multitelescopes.devices[tel_name]
            
        def _searchobs(target, singletelescope, abort_action):
            kwargs = dict(exptime = target['exptime'], 
                        count = target['count'],
                        filter_ = target['filter_'],
                        binning = target['binning'], 
                        imgtype = 'Light', 
                        ra = target['RA'],
                        dec = target['De'], 
                        name = target['objname'],
                        obsmode = 'Search',
                        objtype = target['objtype'],
                        ntelescope = 1,
                        autofocus_before_start = True,
                        autofocus_when_filterchange= True)
            self.DB.Daily.update_target(update_value = 'scheduled', update_key = 'status', id_value = target['id'], id_key = 'id')
            action = SingleObservation(singletelescope= singletelescope, abort_action = abort_action)
            action_id = uuid.uuid4().hex
            # Pop the telescope from the tel_queue
            tel_name = singletelescope.tel_name
            self.tel_queue.pop(tel_name, None)
            # Appedd the action and telescope to the action_queue
            self.action_queue.append({'target': target['objname'], 'action': action, 'tel' : singletelescope, 'id' : action_id})
            
            # Run observation
            result_action = action.run(**kwargs)
            
            # Update the target status
            if result_action:
                self.DB.Daily.update_target(update_value = 'observed', update_key = 'status', id_value = target['id'], id_key = 'id')
            else:
                self.DB.Daily.update_target(update_value = 'failed', update_key = 'status', id_value = target['id'], id_key = 'id')
            # Pop the action and telescope from the action_queue
            self.action_queue = [item for item in self.action_queue if item.get('id') != action_id]
            # Apped the telescope to the tel_queue
            self.tel_queue[tel_name] = singletelescope

        def _singleobs(target, singletelescope, abort_action):
            kwargs = dict(exptime=target['exptime'], 
                        count = target['count'],
                        filter_ = target['filter_'],
                        binning = target['binning'], 
                        imgtype = 'Light', 
                        ra = target['RA'],
                        dec = target['De'], 
                        name = target['objname'],
                        obsmode = 'Single',
                        objtype = target['objtype'],
                        ntelescope = 1,
                        autofocus_before_start = True,
                        autofocus_when_filterchange= True)
            self.DB.Daily.update_target(update_value = 'scheduled', update_key = 'status', id_value = target['id'], id_key = 'id')
            action = SingleObservation(singletelescope= singletelescope, abort_action = abort_action)
            action_id = uuid.uuid4().hex
            # Pop the telescope from the tel_queue
            tel_name = singletelescope.tel_name
            self.tel_queue.pop(tel_name, None)
            # Appedd the action and telescope to the action_queue
            self.action_queue.append({'target': target['objname'], 'action': action, 'tel' : singletelescope, 'id' : action_id})
            
            # Run observation
            result_action = action.run(**kwargs)
            
            # Update the target status
            if result_action:
                self.DB.Daily.update_target(update_value = 'observed', update_key = 'status', id_value = target['id'], id_key = 'id')
            else:
                self.DB.Daily.update_target(update_value = 'failed', update_key = 'status', id_value = target['id'], id_key = 'id')
            # Pop the action and telescope from the action_queue
            self.action_queue = [item for item in self.action_queue if item.get('id') != action_id]
            # Apped the telescope to the tel_queue
            self.tel_queue[tel_name] = singletelescope
        
        obsmode = target['obsmode'].upper()        
        if obsmode == 'SPEC':
            ntelescope = target['ntelescope']
            if len(self.tel_queue) == 1: ####################################################
                multi_tel = self.multitelescopes
                thread = Thread(target= _specobs, kwargs = {'target' : target, 'multitelescopes' : multi_tel, 'abort_action' : abort_action}, daemon = False)
                thread.start()
        elif obsmode == 'DEEP':
            ntelescope = target['ntelescope']
            if len(self.tel_queue) >= ntelescope:
                multi_tel = MultiTelescopes(SingleTelescope_list = [self.tel_queue.popitem()[1] for i in range(ntelescope)])
                thread = Thread(target= _deepobs, kwargs = {'target' : target, 'multitelescopes' : multi_tel, 'abort_action' : abort_action}, daemon = False)
                thread.start()
        elif obsmode == 'SEARCH':
            ntelescope = target['ntelescope']
            if len(self.tel_queue) >= 1:
                tel_name, single_tel = self.tel_queue.popitem()
                thread = Thread(target= _searchobs, kwargs = {'target' : target, 'singletelescope' : single_tel, 'abort_action' : abort_action}, daemon = False)
                thread.start()
        else:
            if len(self.tel_queue) >= 1:
                tel_name, single_tel = self.tel_queue.popitem()
                thread = Thread(target= _singleobs, kwargs = {'target' : target, 'singletelescope' : single_tel, 'abort_action' : abort_action}, daemon = False)
                thread.start()
        
        
    def _update_DB(self,
                  utctime : Time = Time.now()):
        print('Updating databases...')
        db = DB(utctime = utctime)
        print('DB Updated')
        return db
    
    def run(self):
        
        obsnight = self.DB.Daily.obsnight        
        obs_start_time = obsnight.sunset_astro
        obs_end_time = obsnight.sunrise_astro
        now = Time.now()
        is_ToO_triggered = False
        while now < obs_end_time:
            self.DB.Daily.initialize(initialize_all = False)
            time.sleep(0.5)
            best_target, score = self.DB.Daily.best_target(utctime = now)
            print(f'Best target: {best_target["objname"]}')
            obsmode = best_target['obsmode'].upper()
            objtype = best_target['objtype'].upper()
            is_obs_triggered = True
            if not is_ToO_triggered:
                abort_observation = Event()
            
            if obsmode == 'SPEC':
                ntelescope = best_target['ntelescope']
                if len(self.tel_queue) == 1:
                    multi_tel = self.multitelescopes
                    thread = Thread(target= self._specobs, kwargs = {'target' : best_target, 'multitelescopes' : multi_tel, 'abort_action' : abort_observation}, daemon = False)
                    thread.start()
                else:
                    is_obs_triggered = False
                    pass
            elif obsmode == 'DEEP':
                ntelescope = best_target['ntelescope']
                if len(self.tel_queue) >= ntelescope:
                    multi_tel = MultiTelescopes(SingleTelescope_list = [self.tel_queue.popitem()[1] for i in range(ntelescope)])
                    thread = Thread(target= self._deepobs, kwargs = {'target' : best_target, 'multitelescopes' : multi_tel, 'abort_action' : abort_observation}, daemon = False)
                    thread.start()
                else:
                    is_obs_triggered = False
                    pass
            elif obsmode == 'SEARCH':
                ntelescope = best_target['ntelescope']
                if len(self.tel_queue) >= 1:
                    tel_name, single_tel = self.tel_queue.popitem()
                    thread = Thread(target= self._searchobs, kwargs = {'target' : best_target, 'singletelescope' : single_tel, 'abort_action' : abort_observation}, daemon = False)
                    thread.start()
                else:
                    is_obs_triggered = False
                    pass
            else:
                if len(self.tel_queue) >= 1:
                    tel_name, single_tel = self.tel_queue.popitem()
                    thread = Thread(target= self._singleobs, kwargs = {'target' : best_target, 'singletelescope' : single_tel, 'abort_action' : abort_observation}, daemon = False)
                    thread.start()
                else:
                    is_obs_triggered = False
                    pass
            if (objtype == 'TOO') & (~abort_observation.is_set()):
                is_ToO_triggered = True
                abort_observation.set()
            if is_obs_triggered:
                print(f'Observation on {best_target["objname"]} is triggered')
            print(f'tel_queue: {self.tel_queue}')
            #print(f'action_queue: {self.action_queue}')
            time.sleep(1)
                
                
            # Define multitelescopes 
        
    def put_action(self, target, action, telescopes, action_id):
        # Acquire the lock before putting action into the action queue
        self.action_lock.acquire()
        try:
            # Put action and corresponding telescopes into the action queue
            self.action_queue.append({'target': target['objname'], 'action': action, 'tel' : telescopes, 'id' : action_id})
        finally:
            # Release the lock
            self.action_lock.release()
            
    def pop_action(self, action_id):
        # Acquire the lock before putting action into the action queue
        self.action_lock.acquire()
        try:
            # Put action and corresponding telescopes into the action queue
            self.action_queue = [item for item in self.action_queue if item.get('id') != action_id]
        finally:
            # Release the lock
            self.action_lock.release()
            
    def put_telescope(self, telescope):
        # Acquire the lock before modifying self.used_telescopes
        self.tel_lock.acquire()
        try:
            # Append telescopes used in the action to the list
            self.tel_queue[telescope.tel_name] = telescope
        finally:
            # Release the lock
            self.tel_lock.release()
            
    def pop_telescope(self, telescope):
        # Acquire the lock before modifying self.used_telescopes
        self.tel_lock.acquire()
        try:
            # Append telescopes used in the action to the list
            self.tel_queue.pop(telescope.tel_name, None)
        finally:
            # Release the lock
            self.tel_lock.release()
    
    
# %%

M = MultiTelescopes([SingleTelescope(21)])
abort_action = Event()
R = NightObservation(M, abort_action= abort_action)
# %%
import astropy.units as u
target, score = R.DB.Daily.best_target(utctime = Time.now())
#R.DB.Daily.update_target(update_value = 'scheduled', update_key = 'status', id_value = target['id'], id_key = 'id')
# %%
R.DB.Daily.update_target(update_value = 'scheduled', update_key = 'status', id_value = target['id'], id_key = 'id')
# %%
target
# %%
R.initialize()
# %%
R.run()
# %%
