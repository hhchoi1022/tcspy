
#%%
import multiprocessing
from multiprocessing import Lock
import time
from multiprocessing import Manager
from multiprocessing import Process

class Test:
    def __init__(self,
                 telescopes : list,
                 tel_names : list):
        manager = Manager()
        self.multitelescopes = telescopes
        self.names = tel_names
        self.tel_queue = manager.dict()
        self.action_queue = manager.list()
        self.tel_lock = Lock()

    def initialize(self):
        for telescope, tel_name in zip(self.multitelescopes, self.names):
            Process(target=self.put_telescope, args=(telescope, tel_name), daemon=False).start()
            #self._put_telescope(telescope = self.multitelescopes.devices[tel_name])
            #self.tel_queue[tel_name] = self.multitelescopes.devices[tel_name]
        
    def put_telescope(self, telescope, tel_name):
        # Acquire the lock before modifying self.used_telescopes
        self.tel_lock.acquire()
        try:
            # Append telescopes used in the action to the list
            #if self._is_tel_ready(status):
            self.tel_queue[tel_name] = telescope
        finally:
            # Release the lock
            self.tel_lock.release()

    def pop_telescope(self, tel_name):
        # Acquire the lock before modifying self.used_telescopes
        self.tel_lock.acquire()
        try:
            # Append telescopes used in the action to the list
            self.tel_queue.pop(tel_name, None)
        finally:
            # Release the lock
            self.tel_lock.release()
    
    def put_action(self, action):
        self.action_queue.append(action)
        print(f"Action {action} added to the queue.")

    def pop_action(self):
        if self.action_queue:
            action = self.action_queue.pop(0)
            print(f"Action {action} removed from the queue.")
            return action
        print("Action queue is empty.")
        return None

    def observation(self):
        telescope = self.pop_telescope()
        if telescope:
            self.put_action(f"Observing with {telescope}")
            time.sleep(10)
            action = self.pop_action()
            if action:
                print(f"Completed {action}.")
            self.put_telescope(telescope)
#%%
from multiprocessing import Lock, Manager, Process

class Test:
    def __init__(self, telescopes: list, tel_names: list):
        manager = Manager()
        self.multitelescopes = telescopes
        self.names = tel_names
        self.tel_queue = manager.dict()
        self.action_queue = manager.list()
        self.tel_lock = Lock()

    def initialize(self):
        for telescope, tel_name in zip(self.multitelescopes, self.names):
            # Pass arguments as a tuple (telescope, tel_name)
            Process(target=self.put_telescope, args=(telescope, tel_name), daemon=False).start()

    def put_telescope(self, telescope, tel_name):
        # Acquire the lock before modifying self.tel_queue
        self.tel_lock.acquire()
        try:
            self.tel_queue[tel_name] = telescope
        finally:
            # Release the lock
            self.tel_lock.release()

if __name__ == "__main__":

    # Add initial telescopes to the queue
    initial_telescopes = ["Telescope1", "Telescope2", "Telescope3"]
    initial_telnames = ["tel1", "tel2", "tel3"]
    test = Test(initial_telescopes, initial_telnames)
    test.initialize()
#%%
    for telescope in initial_telescopes:
        test.put_telescope(telescope, telescope)

    # Create observation processes
    processes = []
    for _ in range(3):
        p = multiprocessing.Process(target=test.observation)
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    #for p in processes:
    #    p.join()

    print("All observation processes have completed.")

# %%
from multiprocessing import Queue
# %%
A = Queue()
# %%
A.put(dict(a=1))  
# %%
A.get()
# %%
