#%%
from multiprocessing import Event
from multiprocessing import Manager

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.exception import *

class FansOn(Interface_Runnable, Interface_Abortable):
    
    def __init__(self, 
                 singletelescope : SingleTelescope,
                 abort_action : Event):
        """
        A class representing a FansOn action for a telescope.

        Parameters
        ----------
        singletelescope : SingleTelescope
            An instance of SingleTelescope class representing an individual telescope to perform the action on.
        abort_action : Event
            An instance of the built-in Event class to handle the abort action. 

        Attributes
        ----------
        telescope : SingleTelescope
            The SingleTelescope instance on which the action has to be performed.
        telescope_status : TelescopeStatus
            A TelescopeStatus instance which is used to check the current status of the telescope.
        abort_action : Event
            An instance of Event to handle the abort action.

        Methods
        -------
        run()
            Performs the action to turn on the fans of the telescope.
        abort()
            A function that needs to be defined to enable abort functionality. In this class, it does nothing and should be overridden in subclasses if needed.
        """
        self.telescope = singletelescope
        self.telescope_status = TelescopeStatus(self.telescope)
        self.abort_action = abort_action
        self.shared_memory_manager = Manager()
        self.shared_memory = self.shared_memory_manager.dict()
        self.shared_memory['succeeded'] = False
        self.shared_memory['exception'] = None
        self.shared_memory['is_running'] = False
        self.is_running = False

    def run(self):
        """
        Performs the action to turn on the fans of the telescope.

        Raises
        ------
        ConnectionException
            If the focuser is disconnected.
        AbortionException
            If the operation is aborted.
        ActionFailedException
            If there is an error during the fan operation.
        """
        self.telescope.register_logfile()
        self.telescope.log.info(f'=====LV1[{type(self).__name__}] is triggered.')
        self.is_running = True
        self.shared_memory['is_running'] = True
        self.shared_memory['succeeded'] = False
        # Check device connection
        if self.telescope_status.focuser.lower() == 'disconnected':
            self.telescope.log.critical(f'=====LV1[{type(self).__name__}] is failed: focuser is disconnected.')
            self.shared_memory['exception'] = 'ConnectionException'
            self.shared_memory['is_running'] = False
            self.is_running = False
            raise ConnectionException(f'[{type(self).__name__}] is failed: focuser is disconnected.')
        
        # If not aborted, execute the action
        if self.abort_action.is_set():
            self.telescope.log.warning(f'=====LV1[{type(self).__name__}] is aborted.')
            self.shared_memory['exception'] = 'AbortionException'
            self.shared_memory['is_running'] = False
            self.is_running = False
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
                    
        # Start action
        try:
            result_fanson = self.telescope.focuser.fans_on()
        except FocusFansFailedException:
            self.telescope.log.critical(f'=====LV1[{type(self).__name__}] is failed: fan operation failure.')
            self.shared_memory['exception'] = 'ActionFailedException'
            self.shared_memory['is_running'] = False
            self.is_running = False
            raise ActionFailedException(f'[{type(self).__name__}] is failed: fan operation failure.')          
        if result_fanson:
            self.shared_memory['succeeded'] = True
        
        self.telescope.log.info(f'=====LV1[{type(self).__name__}] is finished.')
        self.shared_memory['is_running'] = False
        self.is_running = False 
        if self.shared_memory['succeeded']:
            return True    
        
    def abort(self):
        self.telescope.register_logfile()
        self.abort_action.set()
        self.telescope.log.warning(f'=====LV1[{type(self).__name__}] is aborted.')
        self.shared_memory['exception'] = 'AbortionException'
        self.shared_memory['is_running'] = False
        self.is_running = False
        raise AbortionException(f'[{type(self).__name__}] is aborted.')
