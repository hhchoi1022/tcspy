#%%
from threading import Thread, Event
from queue import Queue
from tcspy.devices import IntegratedDevice
from typing import List, Union
class MultiAction:
    def __init__(self, 
                 array_telescope : List[IntegratedDevice],
                 array_kwargs : Union[List[dict], dict],
                 function : object
                 ):
        self.array_telescope = array_telescope
        self.array_kwargs = array_kwargs
        if isinstance(array_kwargs, dict):
            num_telescope = len(array_telescope)
            self.array_kwargs = [self.array_kwargs.copy() for i in range(num_telescope)]
        self.function = function
        self.abort_action = Event()
        self.multithreads = None
        self.queue = None
        self._set_multithreads()
        
    
    def _set_multithreads(self):
        self.queue = Queue()
        def consumer(abort_action):
            while not self.abort_action.is_set():                
                params = self.queue.get()
                telescope = params['telescope']
                kwargs = params['kwargs']
                func = self.function(telescope, abort_action = abort_action)
                func.run(**kwargs)
        self.dict_threads = dict()
        for telescope in self.array_telescope:
            self.dict_threads[telescope.unitnum] = Thread(target= consumer, kwargs = {'abort_action' : self.abort_action}, daemon = False)
            self.dict_threads[telescope.unitnum].start()

    def run(self):
        for telescope, kwargs in zip(self.array_telescope, self.array_kwargs):
            self.queue.put({"telescope": telescope, "kwargs": kwargs })
    
    def abort(self):
        self.abort_action.set()
        self.queue = Queue()
        def consumer(abort_action):
            while True:
                params = self.queue.get()
                telescope = params['telescope']
                kwargs = params['kwargs']
                func = self.function(telescope, abort_action = abort_action)
                func.abort()
        for telescope in self.array_telescope:
            thread = Thread(target= consumer, kwargs = {'abort_action' : self.abort_action}, daemon = False)
            thread.start()
            
        for telescope, kwargs in zip(self.array_telescope, self.array_kwargs):
            self.queue.put({"telescope": telescope, "kwargs": kwargs })
#%% Define telescopes
IntDevice_1 = IntegratedDevice(unitnum = 6, tel_type = 'pwi')
IntDevice_2 = IntegratedDevice(unitnum = 7, tel_type = 'pwi')
array_telescope = list([IntDevice_1, IntDevice_2])

# Test
"""LEVEL 1"""
#%% Connect/Disconnect
from tcspy.action.level1 import Connect, Disconnect
array_kwargs = dict()
A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs, function= Connect)
#A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs, function= Disconnect)
A.run()
#%%
A.abort()

#%% TrackingOn/Off
from tcspy.action.level1 import TrackingOn, TrackingOff
array_kwargs_trackingon = dict()
array_kwargs_trackingoff = dict()
A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs_trackingon, function= TrackingOn)
A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs_trackingoff, function= TrackingOff)
A.run()
#%%
A.abort()

#%% Cool/Warm
from tcspy.action.level1 import Cool, Warm
array_kwargs_cool = dict(settemperature = -15, tolerance = 1)
array_kwargs_warm = dict(settemperature = 10, tolerance = 1)
A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs_cool, function= Cool)
#A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs_warm, function= Warm)
A.run()
#%%
A.abort()

#%% Park/Unpark
from tcspy.action.level1 import Park, Unpark
array_kwargs = dict()
A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs, function= Park)
#A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs, function= Unpark)
A.run()
#%%
A.abort()

#%% SlewAltAz/SlewRADec
from tcspy.action.level1.slewAltAz import SlewAltAz
from tcspy.action.level1.slewRADec import SlewRADec
array_kwargs_slewAltAz = dict(alt = 40,
                              az  = 270,
                              tracking = False)
array_kwargs_slewRADec = dict(ra = 300,
                              dec  = 40,
                              tracking = False)
A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs_slewAltAz, function= SlewAltAz)
#A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs_slewRADec, function= SlewRADec)
A.run()
#%%
A.abort()

#%% ChangeFilter
from tcspy.action.level1 import ChangeFilter
array_kwarg1 = dict(filter_ = 'm400')
array_kwarg2 = dict(filter_ = 'm450')
array_kwargs = list([array_kwarg1, array_kwarg2])
A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs, function= ChangeFilter)
A.run()
#%%
A.abort()

#%% ChangeFocus
from tcspy.action.level1 import ChangeFocus
array_kwargs = dict(position = 10000)
A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs, function= ChangeFocus)
A.run()
#%%
A.abort()


"""LEVEL 2"""
#%%
from tcspy.action.level1.exposure import Exposure
from tcspy.utils.target import mainTarget
from tcspy.devices.observer import mainObserver
target_NGC1566 = mainTarget(unitnum = 1, observer = mainObserver(unitnum = 1), target_alt = 30, target_az= 270, target_name = 'NGC1566')
array_kwargs_1 = dict(frame_number = 0,
                    exptime = 5,
                    filter_ = 'm400',
                    imgtype = 'light',
                    binning = 1,
                    target_name = None,
                    target = target_NGC1566
                    )
array_kwargs_2 = dict(frame_number = 0,
                    exptime = 5,
                    filter_ = 'm450',
                    imgtype = 'light',
                    binning = 1,
                    target_name = None,
                    target = target_NGC1566
                    )
array_kwargs = list([array_kwargs_1, array_kwargs_2])
A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs, function= Exposure)
A.run()
#%%
A.abort()
#%%
from tcspy.action.level2.singleobservation import SingleObservation
from tcspy.utils.target import mainTarget
from tcspy.devices.observer import mainObserver
target_NGC1566 = mainTarget(unitnum = 1, observer = mainObserver(unitnum = 1),target_ra = 300, target_dec = 60, target_alt = 30, target_az= 270, target_name = 'NGC1566')
array_kwargs_1 = dict(exptime = 5,
                      count  = 1,
                      filter_  = 'm425',
                      imgtype  = 'Light',
                      binning  = 1,
                      ra  = None,
                      dec  = None,
                      alt  = 40,
                      az  = 300,
                      target_name  = 'Test'
                      )

array_kwargs_2 = dict(exptime = 5,
                      count  = 1,
                      filter_  = 'm475',
                      imgtype  = 'Light',
                      binning  = 1,
                      ra  = None,
                      dec  = None,
                      alt  = 50,
                      az  = 270,
                      target_name  = 'Test'
                      #target  = target_NGC1566
                      )
array_kwargs = list([array_kwargs_1, array_kwargs_2])
A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs, function= SingleObservation)
#%%
A.run()
#%%
A.abort()
#%%
