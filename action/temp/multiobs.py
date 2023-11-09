#%%
import threading
from threading import Thread
from queue import Queue
from action.slew_tmp import Slew_AltAz
from tcspy.devices import IntegratedDevice
#%%
in_queue = Queue(maxsize = 0)

def consumer(q : Queue, function : object):
    while True:
        print('Consumer waiting')
        kwargs = q.get()  # 두 번째로 완료
        function(**kwargs)
        print('Consumer working')
        # 작업 수행
        # ...
        print('Consumer done')
        q.task_done()  # 세 번째로 완료
#%%
#quitsignal = threading.Event()
#thread = Thread(target=worker, kwargs = {'q' : in_queue, 'function' : Slew_AltAz, 'quit': quitsignal}, daemon = True)
def multi_action(MultiDevice : list(IntegratedDevice), function, **kwargs):
    in_queue = Queue
    for integrated_device in MultiDevice:
        
    for i in range(2):
        thread = Thread(target=consumer, kwargs = {'q' : in_queue, 'function' : function}, daemon = True)
thread1 = Thread(target=consumer, kwargs = {'q' : in_queue, 'function' : Slew_AltAz}, daemon = True)
thread2 = Thread(target=consumer, kwargs = {'q' : in_queue, 'function' : Slew_AltAz}, daemon = True)
# %%
IntDevice_1 = IntegratedDevice(unitnum = 1)
IntDevice_2 = IntegratedDevice(unitnum = 2)
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
from tcspy.action.slew import Slew
from tcspy.devices import IntegratedDevice
#%%
def consumer(q: Queue, function: object, results: list):
    while True:
        action = q.get()
        if action is None:
            break
        #print(f'Consumer for unitnum {action["devices"].unitnum} waiting')
        result = function(**action)
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
IntDevice_1 = IntegratedDevice(unitnum=1)
IntDevice_2 = IntegratedDevice(unitnum=2)
Slew1 = Slew(IntDevice_1)
Slew2 = Slew(IntDevice_2)

thread1 = Thread(target=consumer, args=(q, Slew1.slew_AltAz, results), daemon=True)
thread2 = Thread(target=consumer, args=(q, Slew2.slew_AltAz, results), daemon=True)
# Start the consumer threads
thread1.start()
thread2.start()
#%%
# Define actions for unitnum 1 and 2
action1 = {
    "alt": 0,
    "az": 270
}

action2 = {
    "alt": 40,
    "az": 270
}

action3 = {
    "alt": 30,
    "az": 260
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
