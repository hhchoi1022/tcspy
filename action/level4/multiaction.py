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
        def consumer(telescope, abort_action):
            while not self.abort_action.is_set():
                func = self.function(telescope, abort_action = abort_action)
                kwargs = self.queue.get()
                func.run(**kwargs)
                #self.queue.task_done()
        thread_dict = dict()
        for telescope in self.array_telescope:
            thread_dict[telescope.unitnum] = Thread(target= consumer, kwargs = {'telescope' : telescope, 'abort_action' : self.abort_action}, daemon = False)
        self.multithreads = thread_dict

    def run(self):
        for unit, thread in self.multithreads.items():
            thread.start()
        
        for kwargs in self.array_kwargs:
            self.queue.put(kwargs)
    
    def abort(self):
        self.abort_action.set()
        self.queue = Queue()
        def consumer(telescope, abort_action):
            while True:
                func = self.function(telescope, abort_action = abort_action)
                kwargs = self.queue.get()
                func.abort()
                #self.queue.task_done()
        local_abort_action = Event()
        for telescope in self.array_telescope:
            thread = Thread(target= consumer, kwargs = {'telescope' : telescope, 'abort_action' : local_abort_action}, daemon = False)
            thread.start()
            
        for kwargs in self.array_kwargs:
            self.queue.put(kwargs)
IntDevice_1 = IntegratedDevice(unitnum = 1)
IntDevice_2 = IntegratedDevice(unitnum = 2)
array_telescope = list([IntDevice_1, IntDevice_2])
#%%
from tcspy.action.level1 import Connect
from tcspy.action.level1 import Disconnect
array_kwargs = dict()
A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs, function= Connect)
#A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs, function= Disconnect)
A.run()
#%%
from tcspy.action.level1 import Park
#%%
array_kwargs = dict()
A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs, function= Park)
A.run()
#%%
A.abort()
#%%
from tcspy.action.level1 import Unpark
array_kwargs = dict()
A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs, function= Unpark)
A.run()
#%%
from tcspy.action.level1.slewAltAz import SlewAltAz
array_kwargs = dict(alt = 50,
                    az  = 270)
A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs, function= SlewAltAz)
A.run()
#%%
A.abort()
#%%
from action.level1.exposure import Exposure
array_kwargs = dict(frame_number = 0,
                    exptime = 5,
                    filter_ = 'm400',
                    imgtype = 'light',
                    binning = 1,
                    target_name = None,
                    target = None
                    )
A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs, function= Exposure)
A.run()
#%%
A.abort()
#%%
from action.level2.singleobservation import SingleObservation
array_kwargs = dict(exptime = 5,
                    count  = 1,
                    filter_  = 'g',
                    imgtype  = 'Light',
                    binning  = 1,
                    ra  = None,
                    dec  = None,
                    alt  = 0,
                    az  = 270,
                    target_name  = 'Test',
                    target  = None
                    )
A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs, function= SingleObservation)
#%%
A.run()
#%%
A.abort()
#%%
