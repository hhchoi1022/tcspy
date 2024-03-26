


#%%
from astropy.time import Time
from threading import Event
import threading
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

#%%


class NightObservation(mainConfig):
    
    def __init__(self, 
                 MultiTelescopes : MultiTelescopes,
                 abort_action : Event,
                 ):
        super().__init__()
        self.multitelescopes = MultiTelescopes
        self.abort_action = abort_action
        self.DB = self.update_DB(utctime = Time.now())
        self.action_queue = list()
        self.tel_queue = dict()
        self.initialize()

        self.action_lock = threading.Lock()
        self.tel_lock = threading.Lock()
    
    def initialize(self):
        
        # Initialize Daily target table 
        self.DB.Daily.initialize(initialize_all= False)
        if all(Time(self.DB.Daily.data['settime']) < Time.now()):
            self.DB.Daily.initialize(initialize_all= True)
        
        # Get status of all telescopes 
        status_devices = self.multitelescopes.status
        for tel_name, status in status_devices.items():
            if self._tel_is_ready(status):
                self.tel_queue[tel_name] = self.multitelescopes.devices[tel_name]

    def _tel_is_ready(self, tel_status_dict):
        ready_tel = tel_status_dict['telescope'] == 'idle'
        ready_cam = tel_status_dict['camera'] == 'idle'
        ready_filt = tel_status_dict['filterwheel'] == 'idle'
        ready_focus = tel_status_dict['focuser'] == 'idle'
        return all([ready_tel, ready_cam, ready_filt, ready_focus])

    def specobs(self, target, multitelescopes, abort_action):
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
        action = SpecObservation(MultiTelescopes= multitelescopes, abort_action = abort_action)
        action_id = uuid.uuid4().hex
        # pop the telescope from the tel_queue
        for tel_name in multitelescopes.devices.keys():
            self.tel_queue.pop(tel_name, None)
        # append the action and telescope to the action_queue
        self.action_queue.append({'action': action, 'tel' : multitelescopes, 'id' : action_id})
        
        action.run(**kwargs)
        
        # append the telescope to the tel_queue
        for tel_name in multitelescopes.devices.keys():
            self.tel_queue[tel_name] = multitelescopes[tel_name]
        # pop the action and telescope from  the action_queue
        self.action_queue = [item for item in self.action_queue if item.get('id') != action_id]
        
    def deepobs(self, target, multitelescopes, abort_action):
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
        action = DeepObservation(MultiTelescopes= multitelescopes, abort_action = abort_action)
        action_id = uuid.uuid4().hex
        # pop the telescope from the tel_queue
        for tel_name in multitelescopes.devices.keys():
            self.tel_queue.pop(tel_name, None)
        # append the action and telescope to the action_queue
        self.action_queue.append({'action': action, 'tel' : multitelescopes, 'id' : action_id})
        
        action.run(**kwargs)
        
        # append the telescope to the tel_queue
        for tel_name in multitelescopes.devices.keys():
            self.tel_queue[tel_name] = multitelescopes[tel_name]
        # pop the action and telescope from  the action_queue
        self.action_queue = [item for item in self.action_queue if item.get('id') != action_id]
    
    def searchobs(self, target, singletelescope, abort_action):
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
        action = SingleObservation(singletelescope= singletelescope, abort_action = abort_action)
        action_id = uuid.uuid4().hex
        # pop the telescope from the tel_queue
        tel_name = singletelescope.tel_name
        self.tel_queue.pop(tel_name, None)
        # append the action and telescope to the action_queue
        self.action_queue.append({'action': action, 'tel' : singletelescope, 'id' : action_id})
        
        action.run(**kwargs)
        
        # append the telescope to the tel_queue
        self.tel_queue[tel_name] = singletelescope
        # pop the action and telescope from  the action_queue
        self.action_queue = [item for item in self.action_queue if item.get('id') != action_id]

    def singleobs(self, target, singletelescope, abort_action):
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
        action = SingleObservation(singletelescope= singletelescope, abort_action = abort_action)
        action_id = uuid.uuid4().hex
        # pop the telescope from the tel_queue
        tel_name = singletelescope.tel_name
        self.tel_queue.pop(tel_name, None)
        # append the action and telescope to the action_queue
        self.action_queue.append({'action': action, 'tel' : singletelescope, 'id' : action_id})
        
        action.run(**kwargs)
        
        # append the telescope to the tel_queue
        self.tel_queue[tel_name] = singletelescope
        # pop the action and telescope from  the action_queue
        self.action_queue = [item for item in self.action_queue if item.get('id') != action_id]
    
    def update_DB(self,
                  utctime : Time = Time.now()):
        print('Updating databases...')
        db = DB(utctime = utctime)
        print('DB Updated')
        return db
    
    def observation(self):
        
        obsnight = self.DB.Daily.obsnight
        
        observation_abort = Event()
        
        obs_start_time = obsnight.sunset_astro
        obs_end_time = obsnight.sunrise_astro
        now = Time.now()
        while now < obs_end_time:
            best_target, score = self.DB.Daily.best_target(utctime = now)
            print(f'Best target: {best_target["objname"]}')
            obsmode = best_target['obsmode'].upper()
            is_obs_triggered = True
            if obsmode == 'SPEC':
                ntelescope = best_target['ntelescope']
                if len(self.tel_queue) == 1:
                    obs_tel = self.multitelescopes
                    thread = Thread(target= self.specobs, kwargs = {'target' : best_target, 'multitelescopes' : obs_tel, 'abort_action' : observation_abort}, daemon = False)
                    thread.start()
                else:
                    is_obs_triggered = False
                    pass
            elif obsmode == 'Deep':
                ntelescope = best_target['ntelescope']
                if self.tel_queue.qsize() >= ntelescope:
                    obs_tel_list = [self.tel_queue.get() for _ in range(ntelescope)]
                    obs_tel = MultiTelescopes(obs_tel_list)
                    action = self.deepobs(target = best_target, multitelescopes= obs_tel, abort_action = observation_abort)
                else:
                    is_obs_triggered = False
                    pass
            elif obsmode == 'Search':
                ntelescope = best_target['ntelescope']
                if self.tel_queue.qsize() >= ntelescope:
                    obs_tel = self.tel_queue.get()
                    action = self.searchobs(target = best_target, multitelescopes= obs_tel, abort_action = observation_abort)
                else:
                    is_obs_triggered = False
                    pass
            else:
                ntelescope = best_target['ntelescope']
                if self.tel_queue.qsize() >= ntelescope:
                    obs_tel = self.tel_queue.get()
                    action = self.singleobs(target = best_target, multitelescopes= obs_tel, abort_action = observation_abort)
                else:
                    is_obs_triggered = False
                    pass
            if is_obs_triggered:
                print(f'Observation on {best_target["objname"]} is triggered')

            time.sleep(1)
                
                
            # Define multitelescopes 
        
    def put_action(self, action, telescopes):
        # Acquire the lock before putting action into the action queue
        self.action_lock.acquire()
        try:
            # Put action and corresponding telescopes into the action queue
            self.action_queue.put((action, telescopes))
        finally:
            # Release the lock
            self.action_lock.release()

    def requeue_telescopes(self, telescopes):
        # Acquire the lock before modifying self.used_telescopes
        self.tel_lock.acquire()
        try:
            # Append telescopes used in the action to the list
            self.used_telescopes.append(telescopes)
        finally:
            # Release the lock
            self.tel_lock.release()

        # Put telescopes back to self.tel_queue
        for telescope in telescopes:
            self.tel_queue.put(telescope)
        
    
    
    
    
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
R.observation()
# %%
