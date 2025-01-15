#%%
from multiprocessing import Event
from multiprocessing import Manager

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.exception import *

class Cool(Interface_Runnable, Interface_Abortable):
    """
    A class representing a cooling action for a single telescope's camera.

    Parameters
    ----------
    singletelescope : SingleTelescope
        An instance of SingleTelescope class representing an individual telescope to perform the action on.
    abort_action : Event
        An instance of the built-in Event class to handle the abort action. 

    Attributes
    ----------
    telescope : SingleTelescope
        The SingleTelescope instance on which the action has to performed.
    telescope_status : TelescopeStatus
        A TelescopeStatus instance which is used to check the current status of the telescope.
    abort_action : Event
        An instance of Event to handle the abort action.

    Methods
    -------
    run(settemperature : float, tolerance : float = 1)
        Performs the action to cool down the telescope camera to a given temperature within a certain tolerance.
    abort()
        A function that stops the cooling action if the camera is already cooling, 
        otherwise it does nothing and should be overridden in subclasses if needed.
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
        Execute the camera cooling.
        
        Parameters
        ----------
        settemperature : float:
            The temperature to set the camera to.
        tolerance : float, optional
            Allowed temperature deviation from the set temperature. Default is 1.

        Returns
        -------
        bool
            True if the cooling action is successful, otherwise an exception is raised.

        Raises
        ------
        ConnectionException
            If the camera on the telescope is disconnected.
        AbortionException
            If the action has been aborted.
        ActionFailedException
            If cooling action fails due to any other reason.
        """
        self.telescope.register_logfile()
        self.telescope.log.info(f'=====LV1[{type(self).__name__}] is triggered.')
        self.is_running = True
        self.shared_memory['is_running'] = True
        self.shared_memory['succeeded'] = False
        # Check device connection
        if self.telescope_status.camera.lower() == 'disconnected':
            self.telescope.log.critical(f'=====LV1[{type(self).__name__}] is failed: camera is disconnected.')
            self.shared_memory['exception'] = 'ConnectionException'
            self.shared_memory['is_running'] = False
            self.is_running = False
            raise ConnectionException(f'[{type(self).__name__}] is failed: camera is disconnected.')
        
        # If not aborted, execute the action
        if self.abort_action.is_set():
            self.abort()
        
        # Start action
        try:
            result_cool = self.telescope.camera.cool(settemperature = settemperature, 
                                                     tolerance = tolerance,
                                                     abort_action = self.abort_action)
        except CoolingFailedException:
            self.telescope.log.critical(f'=====LV1[{type(self).__name__}] is failed: camera cool failure.')
            self.shared_memory['exception'] = 'ActionFailedException'
            self.shared_memory['is_running'] = False
            self.is_running = False
            raise ActionFailedException(f'[{type(self).__name__}] is failed: camera cool failure.')
        except AbortionException:
            self.abort()
        if result_cool:
            self.shared_memory['succeeded'] = True
        
        self.shared_memory['is_running'] = False
        self.is_running = False
        self.telescope.log.info(f'=====LV1[{type(self).__name__}] is finished.')
        if self.shared_memory['succeeded']:
            return True
    
    def abort(self):
        self.abort_action.set()
        self.telescope.log.warning(f'=====LV1[{type(self).__name__}] is aborted.')
        self.shared_memory['exception'] = 'AbortionException'
        self.shared_memory['is_running'] = False
        self.is_running = False
        raise AbortionException(f'[{type(self).__name__}] is aborted.')