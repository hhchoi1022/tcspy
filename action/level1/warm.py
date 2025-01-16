#%%
from multiprocessing import Event
from multiprocessing import Manager

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.exception import * 

class Warm(Interface_Runnable, Interface_Abortable):
    """
    A class to perform the action of warming a telescope.

    Parameters
    ----------
    singletelescope : SingleTelescope
        A SingleTelescope instance to perform the action on.
    abort_action : Event
        An instance of Event to handle the abort action.

    Attributes
    ----------
    telescope : SingleTelescope
        The SingleTelescope instance on which to perform the action.
    telescope_status : TelescopeStatus
        The TelescopeStatus instance used to check the current status of the telescope.
    abort_action : Event
        An instance of Event to handle the abort action.

    Methods
    -------
    run(settemperature, tolerance=1)
        Warm the telescope to a given temperature within a specified tolerance.
    abort()
        This method does nothing but should be overridden in the subclasses if needed.
    """
    
    def __init__(self, 
                 singletelescope : SingleTelescope,
                 abort_action : Event):
        self.telescope = singletelescope
        self.telescope_status = TelescopeStatus(self.telescope)
        self.abort_action = abort_action
        self.shared_memory_manager = Manager()
        self.shared_memory = self.shared_memory_manager.dict()
        self.shared_memory['succeeded'] = False
        self.shared_memory['exception'] = None
        self.shared_memory['is_running'] = False
        self.is_running = False
        
    def run(self,
            settemperature : float,
            tolerance : float = 1):
        """
        Warm the telescope to a given temperature within a specified tolerance.

        Parameters
        ----------
        settemperature : float
            The desired temperature to warm the telescope to.
        tolerance : float, optional
            The accepted deviation from the set temperature.
        
        Raises
        ------
        ConnectionException
            If the telescope is disconnected.
        AbortionException
            If the action was aborted.
        ActionFailedException
            If the warming process failed.
        
        Returns
        -------
        bool
            True if the action is finished, False otherwise.
        """
        self.telescope.register_logfile()
        self.telescope.log.info(f'=====LV1[{type(self).__name__}] is triggered.')
        self.is_running = False
        self.shared_memory['is_running'] = True
        self.shared_memory['succeeded'] = False
        # Check device connection
        if self.telescope_status.camera.lower() == 'disconnected':
            self.telescope.log.critical(f'=====LV1[{type(self).__name__}] is failed: camera is disconnected.')
            self.shared_memory['exception'] = 'ConnectionException'
            self.shared_memory['is_running'] = False
            self.is_running = False
            return ConnectionException(f'[{type(self).__name__}] is failed: camera is disconnected.')

        # If not aborted, execute the action
        if self.abort_action.is_set():
            self.abort()
        
        try:
            result_warm = self.telescope.camera.warm(settemperature = settemperature,
                                                     tolerance= tolerance,
                                                     abort_action = self.abort_action)
        except WarmingFailedException:
            self.telescope.log.critical(f'=====LV1[{type(self).__name__}] is failed: camera warming failure.')
            self.shared_memory['exception'] = 'ActionFailedException'
            self.shared_memory['is_running'] = False
            self.is_running = False
            raise ActionFailedException(f'[{type(self).__name__}] is failed: camera warming failure.')
        except AbortionException:
            self.abort()
        if result_warm:
            self.shared_memory['succeeded'] = True
        
        self.telescope.log.info(f'=====LV1[{type(self).__name__}] is finished.')
        self.shared_memory['is_running'] = False
        self.is_running = False
        if self.shared_memory['succeeded']:
            return True    
        
    def abort(self):
        self.abort_action.set()
        self.telescope.log.warning(f'=====LV1[{type(self).__name__}] is aborted.')
        self.shared_memory['exception'] = 'AbortionException'
        self.shared_memory['is_running'] = False
        self.is_running = False
        raise AbortionException(f'[{type(self).__name__}] is aborted.')

# %%
