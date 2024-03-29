#%%
from threading import Thread, Event
from queue import Queue
from tcspy.devices import SingleTelescope
from typing import List, Union
class MultiAction:
    def __init__(self, 
                 array_telescope : List[SingleTelescope],
                 array_kwargs : Union[List[dict], dict],
                 function : object,
                 abort_action : Event
                 ):
        """
        A class representing the execution of an action on multiple telescopes.

        Parameters
        ----------
        array_telescope : List[SingleTelescope]
            A list with instances of SingleTelescope class representing the telescopes to perform the action on.
        array_kwargs : Union[List[dict], dict]
            If it's a dictionary, then it will be applied to all telescopes. If it's a list, each dictionary in the list will apply to the corresponding telescope.
        function : object
            The function to be executed in each telescope.
        abort_action : Event
            An instance of the built-in Event class to handle the abort action.

        Attributes
        ----------
        array_telescope : List[SingleTelescope]
            The list of SingleTelescope instances.
        array_kwargs : Union[List[dict], dict]
            The kwargs to feed into each function call.
        function : object
            The function to be executed in each telescope.
        abort_action : Event
            The Event instance to handle the abort actions.
        multithreads : None (> to be defined)
            A placeholder for threads for each telescope.
        queue : None (Queue)
            A queue instance to handle the thread consumer's arguments.
        results : dict
            A dictionary to hold the results of each function call.

        Methods
        -------
        run()
            Add the parameters for each thread in the queue.
        abort()
            Abort the ongoing action.
        get_results()
            Retrieve the results for each telescope's executed action.
        """
        self.array_telescope = array_telescope
        self.array_kwargs = array_kwargs
        if isinstance(array_kwargs, dict):
            num_telescope = len(array_telescope)
            self.array_kwargs = [self.array_kwargs.copy() for i in range(num_telescope)]
        self.function = function
        self.abort_action = abort_action
        self.multithreads = None
        self.queue = None
        self.results = dict()
        self._set_multithreads()
        
    
    def _set_multithreads(self):
        self.queue = Queue()
        def consumer(abort_action):
            while not self.abort_action.is_set():                
                params = self.queue.get()
                telescope = params['telescope']
                tel_name = telescope.name
                kwargs = params['kwargs']
                func = self.function(telescope, abort_action = abort_action)
                result = func.run(**kwargs)
                self.results[tel_name] = result
                
        self.dict_threads = dict()
        for telescope in self.array_telescope:
            self.dict_threads[telescope.unitnum] = Thread(target= consumer, kwargs = {'abort_action' : self.abort_action}, daemon = False)
            self.dict_threads[telescope.unitnum].start()

    def run(self):
        """
        Add the parameters for each thread in the queue.
        """
        for telescope, kwargs in zip(self.array_telescope, self.array_kwargs):
            self.queue.put({"telescope": telescope, "kwargs": kwargs })
    
    def abort(self):
        """
        Abort the ongoing action.
        """
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
    
    def get_results(self):
        """
        Retrieve the results for each telescope's executed action.

        Returns
        -----
        results : dict
            A dictionary with the results of each function call.

        """
        return self.results
