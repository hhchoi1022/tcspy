#%%
from typing import List
from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.devices.observer import mainObserver
from tcspy.utils.logger import mainLogger
from concurrent.futures import ThreadPoolExecutor

#%%

class MultiTelescopes:
    
    def __init__(self, 
                 SingleTelescope_list : List[SingleTelescope]):
        self._devices_list = SingleTelescope_list
        self.devices = self._get_telescopes()
        self.log = self._get_all_logs()
        self.observer = mainObserver()
        
    def __repr__(self):
        txt=  f'MultiTelescopes[{list(self.devices.keys())}]'
        return txt
    
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
    
    def add(self,
            SingleTelescope : SingleTelescope):
        telescope_name = SingleTelescope.name
        log = mainLogger(unitnum = SingleTelescope.unitnum, logger_name = __name__+str(SingleTelescope.unitnum)).log()
        self.devices[telescope_name] = SingleTelescope
        self.log[telescope_name] = log
    
    def remove(self,
               telescope_name):
        self.devices.pop(telescope_name)
        self.log.pop(telescope_name)
    '''
    @property
    def status(self):
        telescopes_status_dict = dict()
        for telescope in self._devices_list:
            name_telescope = telescope.name
            telescopes_status_dict[name_telescope] = TelescopeStatus(telescope).dict
        return telescopes_status_dict'''

    @property
    def status(self):
        with ThreadPoolExecutor() as executor:
            # Submit each telescope to the executor
            futures = {executor.submit(self._get_device_status, device): device for device in self._devices_list}
            # Wait for all futures to complete and collect results
            status_dict = {futures[future].name: future.result() for future in futures}
        
        return status_dict

    def _get_device_status(self, device):
        return TelescopeStatus(device).dict
# %%
if __name__ == '__main__':
    telescope_1 = SingleTelescope(21)
    #telescope_2 = SingleTelescope(2)
    M =  MultiTelescopes([telescope_1])
    #M =  MultiTelescopes([telescope_1, telescope_2])

    import time
    start = time.time()
    A = M.status
    print(time.time() -start)
# %%
