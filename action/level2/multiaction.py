#%%
import threading
from threading import Thread, Event
from queue import Queue
from tcspy.action.level1.slewAltAz import SlewAltAz
from tcspy.action.level1.connect import Connect
from tcspy.devices import IntegratedDevice
from typing import List, Union
#%%
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
        self.abort_event = Event()
        self.multifunc = None
        self.queue = None
        self.set_multiaction()
        
    
    def set_multiaction(self):
        self.queue = Queue()
        def consumer(telescope):
            while True:
                func = self.function(telescope)
                kwargs = self.queue.get()
                func.run(**kwargs)
                self.queue.task_done()
        thread_dict = dict()
        for telescope in self.array_telescope:
            thread_dict[telescope.unitnum] = Thread(target= consumer, kwargs = {'telescope' : telescope}, daemon = True)
        self.multifunc = thread_dict

    def run(self):
        # queue = Queue()
        # def consumer(telescope):
        #     while True:
        #         func = self.function(telescope)
        #         kwargs = queue.get()
        #         func.run(**kwargs)
        #         queue.task_done()
        # thread_dict = dict()
        # for telescope in self.array_telescope:
        #     thread_dict[telescope.unitnum] = Thread(target= consumer, kwargs = {'telescope' : telescope}, daemon = True)

        for unit, thread in self.multifunc.items():
            #print(thread)
            thread.start()
        
        for kwargs in self.array_kwargs:
            self.queue.put(kwargs)
        #queue.join()
    
    def abort(self):
        self.abort_event.set()
        self.queue = Queue()
        def consumer(telescope):
            while True:
                func = self.function(telescope)
                kwargs = self.queue.get()
                func.abort()
                self.queue.task_done()
        thread_dict = dict()
        for telescope in self.array_telescope:
            thread = Thread(target= consumer, kwargs = {'telescope' : telescope}, daemon = True)
            thread.start()
            
        for kwargs in self.array_kwargs:
            self.queue.put(kwargs)

        
        
        
        
        
        
            
#%%
IntDevice_1 = IntegratedDevice(unitnum = 3)
IntDevice_2 = IntegratedDevice(unitnum = 4)
IntDevice_3 = IntegratedDevice(unitnum = 5)
array_telescope = list([IntDevice_1, IntDevice_2, IntDevice_3])
#array_telescope = list([IntDevice_1])
array_kwargs = dict(alt = 70, az  = 0)
#%%
A = MultiAction(array_telescope= array_telescope, array_kwargs= array_kwargs, function= SlewAltAz)
#%%
A.run()
#%%
A.abort()
#%%
from tcspy.action.level1.checkstatus import CheckStatus
c = CheckStatus(IntDevice_1)
stat = c.run()
stat['telescope']

#%%
#%%
action1 = dict(devices = IntDevice_1,
                target_alt = 40,
                target_az = 270,
                target_name = '')
#%%
action2 = dict(devices = IntDevice_2,
                target_alt = 40,
                target_az = 270,
                target_name = '')
# %%
#Slew_AltAz(devices = IntDevice_1, target_alt = 40, target_az = 270)
Slew_AltAz(devices = IntDevice_2, target_alt = 40, target_az = 270)
#%%
in_queue.put(action1)
in_queue.put(action2)
#%%
thread.start()
#in_queue.join()

#%%

# %%
IntDevice_2.tel.slew_altaz(alt = 40, az = 270)
# %%
thread
# %%
IntDevice_2.tel.status
# %%
import threading
import queue

q = queue.Queue()

def worker(q):
    while True:
        item = q.get()
        print(f'Working on {item}')
        print(f'Finished {item}')
        q.task_done()

# Turn-on the worker thread.
threading.Thread(target=worker, kwargs = {'q': q}, daemon=True).start()
#%%
# Send thirty task requests to the worker.
q.put(1)
q.put(2)

# Block until all tasks are done.
q.join()
print('All work completed')
# %%
#%%
from threading import Thread
from queue import Queue
from action.level1.slewAltAz import SlewAltAz
from action.level1.singleobservation import SingleObservation
from tcspy.devices import IntegratedDevice
#%%
def consumer(q: Queue, function: object, results: list):
    while True:
        params = q.get()
        if params is None:
            break
        #print(f'Consumer for unitnum {action["devices"].unitnum} waiting')
        result = function.run(**params)
        results.append(result)  # Store the result in the results list
        #print(f'Consumer for unitnum {action["devices"].unitnum} result: {result}')
        #print(f'Consumer for unitnum {action["devices"].unitnum} working')
        # Perform additional operations if needed
        #print(f'Consumer for unitnum {action["devices"].unitnum} done')
        q.task_done()
#%%
# Create a queue
q = Queue(maxsize=0)
results = []
#%%
# Create IntegratedDevice instances for unitnum 1 and 2
IntDevice_1 = IntegratedDevice(unitnum=3)
IntDevice_2 = IntegratedDevice(unitnum=4)
#%%
action1 = SingleObservation(IntDevice_1)
action2 = SingleObservation(IntDevice_2)
#%%
thread1 = Thread(target=consumer, args=(q, action1, results), daemon=True)
thread2 = Thread(target=consumer, args=(q, action2, results), daemon=True)
# Start the consumer threads
thread1.start()
thread2.start()
#%%
# Define actions for unitnum 1 and 2
action1 = {
    "exptime": 3,
    "count" : 3,
    "alt": 30,
    "az": 300,
    "filter_" : 'r'
}

#%%
# Put actions into the queue for processing
q.put(action1)
q.put(action1)
#%%
#%%
q.put(action1)
q.put(action1)
#%%
q.put(action3)
q.put(action3)

# Wait for all actions to be processed
#q.join()

# Signal the consumer threads to exit
#q.put(None)
#q.put(None)

# Wait for the consumer threads to finish
#thread1.join()
#thread2.join()
#%%
# Now, you can access the results list to work with the results
for i, result in enumerate(results):
    print(f"Result {i+1}: {result}")
# %%
