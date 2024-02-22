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
