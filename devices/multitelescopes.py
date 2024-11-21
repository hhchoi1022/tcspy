#%%
from threading import Thread
from typing import List
from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.devices.observer import mainObserver
from tcspy.utils.logger import mainLogger
from concurrent.futures import ThreadPoolExecutor
import time
from tcspy.configuration import mainConfig
import json
import re

#%%

class MultiTelescopes(mainConfig):
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
                 SingleTelescope_list : List[SingleTelescope] = None):
        super().__init__()
        self._devices_list = SingleTelescope_list
        if not self._devices_list:
            self._load_from_config()
        self._register()
    
    def __repr__(self):
        txt=  f'MultiTelescopes[{list(self.devices.keys())}]'
        return txt
    
    def _load_from_config(self):
        print('Loading multitelescopes...')
        with open(self.config['MULTITELESCOPES_FILE'],'r') as f:
            device_status_all = json.load(f)
        
        def is_telescope_active(telescope_status: dict):
            device_status = all(device['is_active'] for device in telescope_status.values())
            return device_status
        
        list_telescopes = []
        for tel_name, tel_status in device_status_all.items():
            is_tel_active = is_telescope_active(tel_status)
            tel_num = int(re.search(r"\d{2}$", tel_name).group())
            if is_tel_active:
                list_telescopes.append(SingleTelescope(tel_num))
        
        self._devices_list = list_telescopes
        self._register()
        print('Multitelescopes are loaded.')
    
    def _register(self):
        self.devices = self._get_telescopes()
        self.log_dict = self._dict_logs()
        self.log = self._all_logs()
        self.observer = mainObserver()
        self._status_dict = dict()

    
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
        self.log_dict[telescope_name] = log
    
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
        self.log_dict.pop(telescope_name)
        self.log = self._all_logs()

    @property
    def status(self):
        """
        Get the status of all telescopes using ThreadPoolExecutor.

        Returns
        -------
        dict
            A dictionary containing the status of all telescopes.
        """
        thread_list = []
        for device in self._devices_list:
            thread = Thread(target=self._get_device_status, args=(device,))
            thread_list.append(thread)
            thread.start()

        for thread in thread_list:
            thread.join()
        return self._status_dict
    
    @property
    def filters(self):
        filters_dict = dict()
        for telescope in self._devices_list:
            try:
                filters_dict[telescope.name] = telescope.filterwheel.filtnames
            except:
                filters_dict[telescope.name] = None
        return filters_dict
    
    def _get_device_status(self, telescope):
        self._status_dict[telescope. name] = TelescopeStatus(telescope).dict
    
    def _get_telescopes(self):
        telescopes_dict = dict()
        for telescope in self._devices_list:
            telescope_name = telescope.name
            telescopes_dict[telescope_name] = telescope
        return telescopes_dict

    def _dict_logs(self):
        all_logs_dict = dict()
        for telescope in self._devices_list:
            telescope_name = telescope.name
            log = mainLogger(unitnum = telescope.unitnum, logger_name = __name__+str(telescope.unitnum)).log()
            all_logs_dict[telescope_name] = log
        return all_logs_dict

    def _all_logs(self):
        class log: 
            def info(message):
                for log_unit in self.log_dict.values():
                    log_unit.info(message)
            def warning(message):
                for log_unit in self.log_dict.values():
                    log_unit.warning(message)
            def critical(message):
                for log_unit in self.log_dict.values():
                    log_unit.critical(message)
        return log
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
                        SingleTelescope(11),
                        ]
    M = MultiTelescopes(list_telescopes)
    
# %%
