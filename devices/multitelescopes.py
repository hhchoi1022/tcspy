#%%
from threading import Thread
from typing import List
from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.devices.observer import mainObserver
from tcspy.utils.logger import mainLogger
from concurrent.futures import ThreadPoolExecutor
import time

#%%

class MultiTelescopes:
    """
    A class representing multiple telescopes.

    Parameters
    ----------
    SingleTelescope_list : List[SingleTelescope]
        A list of SingleTelescope instances representing individual telescopes.

    Attributes
    ----------
    devices : dict
        A dictionary containing the telescopes with their names as keys and corresponding SingleTelescope instances as values.
    log : dict
        A dictionary containing logger instances of multiple telescopes for each telescope with their names as keys.
    observer : mainObserver
        An instance of the mainObserver class.

    Methods
    -------
    add(singletelescope : SingleTelescope)
        Add a SingleTelescope instance to the MultiTelescopes instance.
    remove(telescope_name)
        Remove a telescope by its name.
    status
        Get the status of all telescopes using ThreadPoolExecutor.
    """
    
    def __init__(self, 
                 SingleTelescope_list : List[SingleTelescope]):
        self._devices_list = SingleTelescope_list
        self.devices = self._get_telescopes()
        self.log = self._get_all_logs()
        self.observer = mainObserver()
        
    def __repr__(self):
        txt=  f'MultiTelescopes[{list(self.devices.keys())}]'
        return txt
    
    def add(self,
            singletelescope : SingleTelescope):
        """
        Add a SingleTelescope instance to the MultiTelescopes instance.

        Parameters
        ----------
        SingleTelescope : SingleTelescope
            The SingleTelescope instance to add.
        """
        telescope_name = singletelescope.name
        log = mainLogger(unitnum = singletelescope.unitnum, logger_name = __name__+str(singletelescope.unitnum)).log()
        self.devices[telescope_name] = singletelescope
        self.log[telescope_name] = log
    
    def remove(self,
               telescope_name):
        """
        Remove a telescope by its name.

        Parameters
        ----------
        telescope_name : str
            The name of the telescope to remove.
        """
        self.devices.pop(telescope_name)
        self.log.pop(telescope_name)
    """
    @property
    def status2(self):
        self._status = dict()
        for tel_name, telescope in self.devices.items():
            Thread(target = self._get_telescope_status, kwargs = dict(telescope=telescope)).start()
        while all(key in self._status for key in self.devices.keys()) == False:
            print(self._status.keys())
            time.sleep(0.005)
        return self._status
    
    def _get_telescope_status(self, telescope):
        self._status[telescope.name] = TelescopeStatus(telescope).dict

    """
    '''
    @property
    def status(self):
        all_status = dict()
        for tel_name, telescope in self.devices.items():
            all_status[tel_name] = TelescopeStatus(telescope).dict
        return all_status
    
    '''
    @property
    def status(self):
        """
        Get the status of all telescopes using ThreadPoolExecutor.

        Returns
        -------
        dict
            A dictionary containing the status of all telescopes.
        """
        with ThreadPoolExecutor() as executor:
            # Submit each telescope to the executor
            futures = {executor.submit(self._get_device_status, device): device for device in self._devices_list}
            # Wait for all futures to complete and collect results
            status_dict = {futures[future].name: future.result() for future in futures}
        
        return status_dict
    
    def _get_device_status(self, telescope):
        return TelescopeStatus(telescope).dict
    
    def _get_telescopes(self):
        telescopes_dict = dict()
        for telescope in self._devices_list:
            telescope_name = telescope.name
            telescopes_dict[telescope_name] = telescope
        return telescopes_dict

    def _get_all_logs(self):
        all_logs_dict = dict()
        for telescope in self._devices_list:
            telescope_name = telescope.name
            log = mainLogger(unitnum = telescope.unitnum, logger_name = __name__+str(telescope.unitnum)).log()
            all_logs_dict[telescope_name] = log
        return all_logs_dict
# %%
if __name__ == '__main__':
    list_telescopes = [SingleTelescope(1),
                         SingleTelescope(2),
                         SingleTelescope(3),
                         SingleTelescope(5),
                         SingleTelescope(6),
                         SingleTelescope(7),
                         SingleTelescope(8),
                         SingleTelescope(9),
                         SingleTelescope(10),
                         SingleTelescope(11),
                         ]
    #telescope_2 = SingleTelescope(2)
    #M =  MultiTelescopes([telescope_1])
    M =  MultiTelescopes(list_telescopes)
#%%
if __name__ == '__main__':
    start = time.time()
    M.status
    print(time.time() -start)
    


# %%
