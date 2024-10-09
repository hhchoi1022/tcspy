#%%
from astropy.time import Time
import astropy.units as u
from multiprocessing import Event, Lock
from threading import Thread
import time
import uuid
from tcspy.action.level1 import *
from tcspy.action.level2 import *
from tcspy.action.level3 import *
from tcspy.configuration import mainConfig
from tcspy.devices import MultiTelescopes
from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.pilot import Shutdown
from tcspy.utils.databases import DB
from tcspy.utils.error import *
from tcspy.utils.target import SingleTarget
from tcspy.utils.exception import *
from tcspy.utils.nightsession import NightSession
#%%


class NightObservation(mainConfig):
    
    def __init__(self, 
                 MultiTelescopes : MultiTelescopes,
                 abort_action : Event,
                 ):
        super().__init__()
        self.multitelescopes = MultiTelescopes
        self.abort_action = abort_action
        self.DB = DB(utctime = Time.now()).Daily
        self.obsnight = NightSession(Time.now()).obsnight_utc
        self.weather = next(iter(self.multitelescopes.devices.values())).devices['weather']
        self.safetymonitor = next(iter(self.multitelescopes.devices.values())).devices['safetymonitor']

        self.autofocus = self.autofocus_config()

        self.action_queue = list()
        self.tel_queue = dict()
        self.tel_lock = Lock()
        self.action_lock = Lock()
        self.is_running = False
        self.is_obs_triggered = False
        self.is_ToO_triggered = False
        self._ToO_abort = Event()
        self._observation_abort = Event()
        self.initialize()
    
    def autofocus_config(self):
        class autofocus_config: 
            def __init__(self):
                self.use_history = True
                self.history_duration = 60 
                self.before_start = True
                self.when_filterchange = True
                self.when_elapsed = True
                self.elapsed_duration = 60
            def __repr__(self):
                txt = ('AUTOFOCUS CONFIGURATION ============\n'+
                       ''.join(f"autofocus.{key} = {value}\n" for key, value in self.__dict__.items())
                        )
                return txt
        return autofocus_config()
        
    def initialize(self):
        
        # Initialize Daily target table 
        self.DB.initialize(initialize_all= True)
        
        # Connect Weather Updater
        Thread(target = self.weather.run, kwargs = dict(abort_action = self.abort_action), daemon = False).start()
        # Connect SafetyMonitor Updater
        Thread(target = self.safetymonitor.run, kwargs = dict(abort_action = self.abort_action), daemon = False).start()

        # Set device for safety check
        if self.config['NIGHTOBS_SAFETYPE'].upper() == 'WEATHER':
            self.is_safe = self._is_weather_safe
        else:
            self.is_safe = self._is_safetymonitor_safe

        # Get status of all telescopes
        #for tel_name, telescope in self.multitelescopes.devices.items():
        #    print(tel_name)
        #    if self._is_tel_ready(TelescopeStatus(telescope).dict):
        #        self.tel_queue[tel_name] = telescope
        status_devices = self.multitelescopes.status
        for tel_name, status in status_devices.items():
            if self._is_tel_ready(status):
                self.tel_queue[tel_name] = self.multitelescopes.devices[tel_name]
        
        # Initialization is finished

    def _is_tel_ready(self, tel_status_dict):
        ready_tel = tel_status_dict['mount'].upper() == 'IDLE'
        ready_cam = tel_status_dict['camera'].upper() == 'IDLE'
        ready_filt = tel_status_dict['filterwheel'].upper() == 'IDLE'
        ready_focus = tel_status_dict['focuser'].upper() == 'IDLE'
        return all([ready_tel, ready_cam, ready_filt, ready_focus])
    
    def _is_weather_safe(self):
        weather_status = self.weather.get_status()
        if weather_status['is_safe'] == True:
            return True
        else:
            return False

    def _is_safetymonitor_safe(self):
        safetymonitor_status = self.safetymonitor.get_status()
        if safetymonitor_status['is_safe'] == True:
            return True
        else:
            return False
    
    def _specobs(self, target, telescopes, abort_action, observation_status):
        kwargs = dict(exptime = target['exptime'], 
                    count = target['count'],
                    specmode = target['specmode'],
                    binning = target['binning'], 
                    gain = target['gain'],
                    imgtype = 'Light', 
                    ra = target['RA'],
                    dec = target['De'], 
                    name = target['objname'],
                    objtype = target['objtype'], 
                    id_ = target['id'],
                    note = target['note'],
                    autofocus_use_history = self.autofocus.use_history,
                    autofocus_history_duration = self.autofocus.history_duration,
                    autofocus_before_start = self.autofocus.before_start,
                    autofocus_when_filterchange = self.autofocus.when_filterchange,
                    autofocus_when_elapsed = self.autofocus.when_elapsed,
                    autofocus_elapsed_duration = self.autofocus.elapsed_duration,
                    observation_status = observation_status)  
        
        self.DB.update_target(update_value = 'scheduled', update_key = 'status', id_value = target['id'], id_key = 'id')
        action = SpecObservation(multitelescopes= telescopes, abort_action = abort_action)
        action_id = uuid.uuid4().hex
        # Pop the telescope from the tel_queue
        self._pop_telescope(telescope = telescopes)
        # Apped the action and telescope to the action_queue
        self._put_action(target = target, action = action, telescopes = telescopes, action_id = action_id)
        
        # Run observation
        try:
            result_action = action.run(**kwargs)
            self.DB.update_target(update_value = 'observed', update_key = 'status', id_value = target['id'], id_key = 'id')
        except AbortionException:
            self.DB.update_target(update_value = 'aborted', update_key = 'status', id_value = target['id'], id_key = 'id')
        except ActionFailedException:
            self.DB.update_target(update_value = 'failed', update_key = 'status', id_value = target['id'], id_key = 'id')
        finally:
            # Pop the action and telescope from  the action_queue
            self._pop_action(action_id = action_id)
            # Apped the telescope to the tel_queue
            self._put_telescope(telescope = telescopes)
        
    def _deepobs(self, target, telescopes, abort_action, observation_status):
        kwargs = dict(exptime = target['exptime'], 
                    count = target['count'],
                    filter_ = target['filter_'],
                    binning = target['binning'], 
                    gain = target['gain'],
                    imgtype = 'Light',
                    ra = target['RA'],
                    dec = target['De'], 
                    name = target['objname'],
                    objtype = target['objtype'], 
                    id_ = target['id'],
                    note = target['note'],
                    autofocus_use_history = self.autofocus.use_history,
                    autofocus_history_duration = self.autofocus.history_duration,
                    autofocus_before_start = self.autofocus.before_start,
                    autofocus_when_filterchange = self.autofocus.when_filterchange,
                    autofocus_when_elapsed = self.autofocus.when_elapsed,
                    autofocus_elapsed_duration = self.autofocus.elapsed_duration,
                    observation_status = observation_status)  

        self.DB.update_target(update_value = 'scheduled', update_key = 'status', id_value = target['id'], id_key = 'id')
        action = DeepObservation(multitelescopes= telescopes, abort_action = abort_action)
        action_id = uuid.uuid4().hex
        # Pop the telescope from the tel_queue
        self._pop_telescope(telescope = telescopes)
        # Apped the action and telescope to the action_queue
        self._put_action(target = target, action = action, telescopes = telescopes, action_id = action_id)
        
        # Run observation
        try:
            result_action = action.run(**kwargs)
            self.DB.update_target(update_value = 'observed', update_key = 'status', id_value = target['id'], id_key = 'id')
        except AbortionException:
            self.DB.update_target(update_value = 'aborted', update_key = 'status', id_value = target['id'], id_key = 'id')
        except ActionFailedException:
            self.DB.update_target(update_value = 'failed', update_key = 'status', id_value = target['id'], id_key = 'id')
        finally:
            # Pop the action and telescope from  the action_queue
            self._pop_action(action_id = action_id)
            # Apped the telescope to the tel_queue
            self._put_telescope(telescope = telescopes)
        
    def _searchobs(self, target, telescopes, abort_action, observation_status):
        kwargs = dict(exptime = target['exptime'], 
                    count = target['count'],
                    filter_ = target['filter_'],
                    binning = target['binning'], 
                    gain = target['gain'],
                    imgtype = 'Light', 
                    ra = target['RA'],
                    dec = target['De'], 
                    name = target['objname'],
                    obsmode = 'Search',
                    objtype = target['objtype'],
                    id_ = target['id'],
                    note = target['note'],
                    ntelescope = 1,
                    autofocus_use_history = self.autofocus.use_history,
                    autofocus_history_duration = self.autofocus.history_duration,
                    autofocus_before_start = self.autofocus.before_start,
                    autofocus_when_filterchange = self.autofocus.when_filterchange,
                    autofocus_when_elapsed = self.autofocus.when_elapsed,
                    autofocus_elapsed_duration = self.autofocus.elapsed_duration,
                    observation_status = observation_status)    

        self.DB.update_target(update_value = 'scheduled', update_key = 'status', id_value = target['id'], id_key = 'id')
        action = SingleObservation(singletelescope= telescopes, abort_action = abort_action)
        action_id = uuid.uuid4().hex
        # Pop the telescope from the tel_queue
        self._pop_telescope(telescope = telescopes)
        # Appedd the action and telescope to the action_queue
        self._put_action(target = target, action = action, telescopes = telescopes, action_id = action_id)
        
        # Run observation
        try:
            result_action = action.run(**kwargs)
            self.DB.update_target(update_value = 'observed', update_key = 'status', id_value = target['id'], id_key = 'id')
        except AbortionException:
            self.DB.update_target(update_value = 'aborted', update_key = 'status', id_value = target['id'], id_key = 'id')
        except ActionFailedException:
            self.DB.update_target(update_value = 'failed', update_key = 'status', id_value = target['id'], id_key = 'id')
        finally:
            # Pop the action and telescope from  the action_queue
            self._pop_action(action_id = action_id)
            # Apped the telescope to the tel_queue
            self._put_telescope(telescope = telescopes)

    def _singleobs(self, target, telescopes, abort_action, observation_status):
        kwargs = dict(exptime=target['exptime'], 
                    count = target['count'],
                    filter_ = target['filter_'],
                    binning = target['binning'], 
                    gain = target['gain'],
                    imgtype = 'Light', 
                    ra = target['RA'],
                    dec = target['De'], 
                    name = target['objname'],
                    obsmode = 'Single',
                    objtype = target['objtype'],
                    id_ = target['id'],
                    note = target['note'],
                    ntelescope = 1,
                    autofocus_use_history = self.autofocus.use_history,
                    autofocus_history_duration = self.autofocus.history_duration,
                    autofocus_before_start = self.autofocus.before_start,
                    autofocus_when_filterchange = self.autofocus.when_filterchange,
                    autofocus_when_elapsed = self.autofocus.when_elapsed,
                    autofocus_elapsed_duration = self.autofocus.elapsed_duration,
                    observation_status = observation_status)          

        self.DB.update_target(update_value = 'scheduled', update_key = 'status', id_value = target['id'], id_key = 'id')
        action = SingleObservation(singletelescope= telescopes, abort_action = abort_action)
        action_id = uuid.uuid4().hex
        # Pop the telescope from the tel_queue
        self._pop_telescope(telescope = telescopes)
        # Appedd the action and telescope to the action_queue
        self._put_action(target = target, action = action, telescopes = telescopes, action_id = action_id)

        # Run observation
        try:
            result_action = action.run(**kwargs)
            self.DB.update_target(update_value = 'observed', update_key = 'status', id_value = target['id'], id_key = 'id')
        except AbortionException:
            self.DB.update_target(update_value = 'aborted', update_key = 'status', id_value = target['id'], id_key = 'id')
        except ActionFailedException:
            self.DB.update_target(update_value = 'failed', update_key = 'status', id_value = target['id'], id_key = 'id')
        finally:
            # Pop the action and telescope from  the action_queue
            self._pop_action(action_id = action_id)
            # Apped the telescope to the tel_queue
            self._put_telescope(telescope = telescopes)
    
    def _obstrigger(self, target, abort_action, observation_status = None):     
        obsmode = target['obsmode'].upper()
        if obsmode == 'SPEC':
            if set(self.multitelescopes.devices.keys()) == set(self.tel_queue.keys()): ####################################################
                telescopes = MultiTelescopes(SingleTelescope_list = list(self.tel_queue.values()))
                thread = Thread(target= self._specobs, kwargs = {'telescopes':telescopes, 'target': target, 'abort_action': abort_action, 'observation_status': observation_status}, daemon = False)
                thread.start()
        elif obsmode == 'DEEP':
            ntelescope = target['ntelescope']
            if len(self.tel_queue) >= ntelescope:
                telescopes = MultiTelescopes(SingleTelescope_list = [self.tel_queue.popitem()[1] for i in range(ntelescope)])
                thread = Thread(target= self._deepobs, kwargs = {'telescopes':telescopes, 'target': target, 'abort_action': abort_action, 'observation_status': observation_status}, daemon = False)
                thread.start()
        elif obsmode == 'SEARCH':
            if len(self.tel_queue) >= 1:
                tel_name, telescopes = self.tel_queue.popitem()
                thread = Thread(target= self._searchobs, kwargs = {'telescopes':telescopes, 'target': target, 'abort_action': abort_action, 'observation_status': observation_status}, daemon = False)
                thread.start()
        else:
            if len(self.tel_queue) >= 1:
                tel_name, telescopes = self.tel_queue.popitem()
                thread = Thread(target= self._singleobs, kwargs = {'telescopes':telescopes, 'target': target, 'abort_action': abort_action, 'observation_status': observation_status}, daemon = False)
                thread.start()   
        return True 
    
    def _obsresume(self, target, telescopes, abort_action, observation_status = None):
        # Check observability
        singletarget = SingleTarget(observer = self.multitelescopes.observer, 
                                    ra = target['RA'], dec = target['De'], 
                                    exptime = target['exptime'], count = target['count'], filter_ = target['filter_'], binning = target['binning'], specmode = target['specmode'])
        is_observable = singletarget.is_observable(utctime= Time.now() + singletarget.exposure_info['exptime_tot'] * u.s)
        obsmode = target['obsmode'].upper()        
        
        if is_observable:
            if obsmode == 'SPEC':
                if set(self.multitelescopes.devices.keys()) == set(self.tel_queue.keys()): ####################################################
                    thread = Thread(target= self._specobs, kwargs = {'telescopes':telescopes, 'target': target, 'abort_action': abort_action, 'observation_status': observation_status}, daemon = False)
                    thread.start()
            elif obsmode == 'DEEP':
                ntelescope = target['ntelescope']
                if len(self.tel_queue) >= ntelescope:
                    thread = Thread(target= self._deepobs, kwargs = {'telescopes':telescopes, 'target': target, 'abort_action': abort_action, 'observation_status': observation_status}, daemon = False)
                    thread.start()
            elif obsmode == 'SEARCH':
                ntelescope = target['ntelescope']
                if len(self.tel_queue) >= 1:
                    thread = Thread(target= self._searchobs, kwargs = {'telescopes':telescopes, 'target': target, 'abort_action': abort_action, 'observation_status': observation_status}, daemon = False)
                    thread.start()
            else:
                if len(self.tel_queue) >= 1:
                    thread = Thread(target= self._singleobs, kwargs = {'telescopes':telescopes, 'target': target, 'abort_action': abort_action, 'observation_status': observation_status}, daemon = False)
                    thread.start()
        else:
            self.multitelescopes.log.warning('Observation cannot be resumed: Target is unobservable')
        return True
    
    def _ToOobservation(self):
        self.is_ToO_triggered = True
        aborted_action = self.abort_observation()
        self.multitelescopes.log.info('ToO is triggered.================================')
        obs_start_time = self.obsnight.sunset_observation
        obs_end_time = self.obsnight.sunrise_observation
        now = Time.now()
        
        # Wait until sunset
        # Wait until sunset
        if now < obs_start_time:
            self.multitelescopes.log.info('Wait until sunset... [%.2f hours left]'%((Time.now() - obs_start_time)*24).value)
            print('Wait until sunset... [%.2f hours left]'%((Time.now() - obs_start_time)*24).value)
        while now < obs_start_time:
            time.sleep(5)
            now = Time.now()
            if self.abort_action.is_set():
                self.multitelescopes.log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
        
        aborted_action_ToO = None
        unsafe_weather_count = 0
        # Trigger observation until sunrise
        while now < obs_end_time:
            if self.abort_action.is_set():
                self.multitelescopes.log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
            now = Time.now()
            
            # Initialize the Daily target tbl
            self.DB.initialize(initialize_all = False)
            time.sleep(0.5)  
            
            # Retrieve best target
            best_target, score = self.DB.best_target(utctime = now)
            
            # Check weather status
            is_weather_safe = self.is_safe()
            aborted_action_ToO = None
            
            # If weather is safe
            if is_weather_safe:    
                unsafe_weather_count = 0  
                # If there is any aborted_action due to unsafe weather, resume the observation
                if aborted_action_ToO:
                    for action in aborted_action_ToO:
                        time.sleep(0.5)
                        if set(action['telescope'].devices.keys()).issubset(self.tel_queue.keys()):
                            if isinstance(action['action'], (SpecObservation, DeepObservation)):
                                observation_status = {tel_name: status['status'] for tel_name, status in action['action'].shared_memory['status'].items()}
                            else:
                                observation_status =  action['action'].shared_memory['status']
                            self._obsresume(target = action['target'], telescopes = action['telescope'], abort_action = self._ToO_abort, observation_status = observation_status)
                    aborted_action = None
                # If there is no observable target
                if not best_target:
                    break
                
                # If ToO is aborted manually
                if not self.is_ToO_triggered:
                    break
                
                # If target is not ToO, finish loop
                objtype = best_target['objtype'].upper()
                if not objtype == 'TOO':
                    break
                # Else; trigger observation
                else:
                    self._obstrigger(target = best_target, abort_action = self._ToO_abort)
            # If weather is unsafe
            else:
                unsafe_weather_count += 1
                aborted_action_ToO = self.abort_ToO()
                self.multitelescopes.log.info(f'[{type(self).__name__} ToO is aborted: Unsafe weather]')
                time.sleep(200)
                self._ToO_abort = Event()
                self.is_ToO_triggered = True
                Shutdown(self.multitelescopes, self.abort_action).run(slew = True, warm = False)
            time.sleep(0.5)
        while len(self.action_queue) > 0:
            print('Waiting for ToO to be finished')
            time.sleep(1)
        self.is_ToO_triggered = False
        print('ToO observation finished', Time.now())
        self.multitelescopes.log.info(f'[{type(self).__name__}] ToO observation is finished')
        self._observation_abort = Event()
        
        for action in aborted_action:
            time.sleep(0.5)
            if set(action['telescope'].devices.keys()).issubset(self.tel_queue.keys()):
                if isinstance(action['action'], (SpecObservation, DeepObservation)):
                    observation_status = {tel_name: status['status'] for tel_name, status in action['action'].shared_memory['status'].items()}
                else:
                    observation_status =  action['action'].shared_memory['status']
                self._obsresume(target = action['target'], telescopes = action['telescope'], abort_action = self._observation_abort, observation_status = observation_status)
        return True
    
    def run(self):
        if not self.is_running:
            Thread(target = self._process).start()
            self.is_running = True
        else:
            self.multitelescopes.log.critical(f'[{type(self).__name__}] cannot be run twice.')
            
    def _process(self):
        self.multitelescopes.log.info(f'[{type(self).__name__}] is triggered.')
        self.is_running = True
        self._observation_abort = Event()
        self._ToO_abort = Event()
        obs_start_time = self.obsnight.sunset_observation
        obs_end_time = self.obsnight.sunrise_observation
        now = Time.now() 
        
        # Wait until sunse
        if now < obs_start_time:
            self.multitelescopes.log.info('Wait until sunset... [%.2f hours left]'%((Time.now() - obs_start_time)*24).value)
            print('Wait until sunset... [%.2f hours left]'%((Time.now() - obs_start_time)*24).value)
        while now < obs_start_time:
            time.sleep(5)
            now = Time.now()
            if self.abort_action.is_set():
                self.multitelescopes.log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
        
        aborted_action = None
        unsafe_weather_count = 0
        # Trigger observation until sunrise
        while now < obs_end_time:
            if self.abort_action.is_set():
                self.multitelescopes.log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException (f'[{type(self).__name__}] is aborted.')
            now = Time.now() 
            
            # Initialize the Daily target tbl
            self.DB.initialize(initialize_all = False)
            time.sleep(0.5)  
            
            # Retrieve best target
            best_target, score = self.DB.best_target(utctime = now)
            
            # Check weather status
            is_weather_safe = self.is_safe()
            
            # If weather is safe
            if is_weather_safe:
                unsafe_weather_count = 0
                # If there is any aborted_action due to unsafe weather, resume the observation
                if aborted_action:
                    for action in aborted_action:
                        time.sleep(0.5)
                        if set(action['telescope'].devices.keys()).issubset(self.tel_queue.keys()):
                            if isinstance(action['action'], (SpecObservation, DeepObservation)):
                                observation_status = {tel_name: status['status'] for tel_name, status in action['action'].shared_memory['status'].items()}
                            else:
                                observation_status =  action['action'].shared_memory['status']
                            self._obsresume(target = action['target'], telescopes = action['telescope'], abort_action = self._observation_abort, observation_status = observation_status)
                    aborted_action = None
                else:
                    if best_target:
                        print(f'Best target: {now.isot, best_target["objname"]}')
                        objtype = best_target['objtype'].upper()
                        if objtype == 'TOO':
                            self._ToOobservation()
                        else:
                            self._obstrigger(target = best_target, abort_action = self._observation_abort)
                    else:
                        print('No observable target exists... Waiting for target being observable or new target input')
            # If weather is unsafe
            else:
                if len(self.action_queue) > 0:
                    aborted_action = self.abort_observation()
                    self.multitelescopes.log.info(f'[{type(self).__name__}] is aborted: Unsafe weather')
                self.multitelescopes.log.info(f'[{type(self).__name__}] is waiting for safe weather condition')
                time.sleep(200)
                Shutdown(self.multitelescopes, self.abort_action).run(slew = True, warm = False)
                self._observation_abort = Event()
            time.sleep(0.5)
        if len(self.action_queue) > 0:
            aborted_action = self.abort_observation()
        time.sleep(10)
        self.is_running = False
        print('observation finished', Time.now())        
        Shutdown(self.multitelescopes, self.abort_action).run(slew = True, warm = False)
        self.multitelescopes.log.info(f'[{type(self).__name__}] is finished')
        
    def _put_action(self, target, action, telescopes, action_id):
        # Acquire the lock before putting action into the action queue
        self.action_lock.acquire()
        try:
            # Put action and corresponding telescopes into the action queue
            self.action_queue.append({'target': target, 'action': action, 'telescope' : telescopes, 'id' : action_id})
        finally:
            # Release the lock
            self.action_lock.release()
            
    def _pop_action(self, action_id):
        # Acquire the lock before putting action into the action queue
        self.action_lock.acquire()
        try:
            # Put action and corresponding telescopes into the action queue
            self.action_queue = [item for item in self.action_queue if item.get('id') != action_id]
        finally:
            # Release the lock
            self.action_lock.release()
            
    def _put_telescope(self, telescope):
        # Acquire the lock before modifying self.used_telescopes
        self.tel_lock.acquire()
        try:
            # Append telescopes used in the action to the list
            if isinstance(telescope, SingleTelescope):
                status = TelescopeStatus(telescope).dict
                tel_name = telescope.tel_name
                #if self._is_tel_ready(status):
                self.tel_queue[tel_name] = telescope
            if isinstance(telescope, MultiTelescopes):
                status_devices = telescope.status
                for tel_name, status in status_devices.items():
                    #if self._is_tel_ready(status):
                    self.tel_queue[tel_name] = self.multitelescopes.devices[tel_name]
        finally:
            # Release the lock
            self.tel_lock.release()

    def _pop_telescope(self, telescope):
        # Acquire the lock before modifying self.used_telescopes
        self.tel_lock.acquire()
        try:
            # Append telescopes used in the action to the list
            if isinstance(telescope, SingleTelescope):
                self.tel_queue.pop(telescope.tel_name, None)
            if isinstance(telescope, MultiTelescopes):
                for tel_name, tel in telescope.devices.items():
                    self.tel_queue.pop(tel_name, None)
        finally:
            # Release the lock
            self.tel_lock.release()
    
    def abort(self):
        # Abort NightObservation
        self.abort_action.set()
        obs_history = None
        if self.is_ToO_triggered:
            obs_history = self.abort_ToO()
        else:
            obs_history = self.abort_observation()
        self.is_running = False
        return obs_history    
    
    def abort_observation(self):
        # Abort ordinary observation
        action_history = self.action_queue
        self._observation_abort.set()
        if len(action_history) > 0:
            for action in action_history:
                action['telescope'].log.warning('Waiting for ordinary observation aborted...')
                # Check process aborted
                while any(action['action'].multiaction.status.values()):
                    time.sleep(0.2)
                # Check telescope ready to observe
                #all_tel_status = {tel_name:self._is_tel_ready(tel_status) for tel_name, tel_status in action['telescope'].status.items()}
                #while not all(all_tel_status.values()):
                #    all_tel_status = {tel_name:self._is_tel_ready(tel_status) for tel_name, tel_status in action['telescope'].status.items()}
                self._pop_action(action_id =action['id'])
                self._put_telescope(telescope = action['telescope'])
                self.DB.update_target(update_value = 'aborted', update_key = 'status', id_value = action['target']['id'], id_key = 'id')

        # Get status of all telescopes
        return action_history
        
    def abort_ToO(self, retract_targets : bool = False):
        # Abort ToO observation
        action_history = self.action_queue
        self._ToO_abort.set()
        if retract_targets:
            targets = self.DB.data
            ToO_targets_unobserved = targets[targets['objtype'].upper() == 'TOO']
            if len(ToO_targets_unobserved) > 0:
                for ToO_target in ToO_targets_unobserved:
                    self.DB.update_target(update_value = 'retracted', update_key = 'status', id_value =  ToO_target['id'], id_key = 'id')
        if len(action_history) > 0:
            for action in action_history:
                self.multitelescopes.log.warning('Waiting for ordinary observation aborted...')
                while any(action['action'].multiaction.status.values()):
                    time.sleep(0.2)
                self._pop_action(action_id =action['id'])
                self._put_telescope(telescope = action['telescope'])   
                self.DB.update_target(update_value = 'aborted', update_key = 'status', id_value = action['target']['id'], id_key = 'id')    
        self.is_ToO_triggered = False
        return action_history

# %%
if __name__ == '__main__':
    list_telescopes = [#SingleTelescope(1),
                         SingleTelescope(2),
                         SingleTelescope(3),
                         SingleTelescope(4),
                         SingleTelescope(5),
                         SingleTelescope(6),
                         SingleTelescope(7),
                         SingleTelescope(8),
                         SingleTelescope(9),
                         SingleTelescope(10),
                         SingleTelescope(11)
                         ]
#%%
if __name__ == '__main__':
    M = MultiTelescopes(list_telescopes)
    abort_action = Event()
    #Startup(multitelescopes= M , abort_action= abort_action).run()
    R = NightObservation(M, abort_action= abort_action)
    #R.run()
# %%
