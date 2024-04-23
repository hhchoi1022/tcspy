#%%
from multiprocessing import Event
from multiprocessing import Manager

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.exception import *

class ChangeFocus(Interface_Runnable, Interface_Abortable):
    """
    A class representing a change focus action for a single telescope.

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
    run(position: int = None, is_relative : bool = False)
        Performs the action to change the focus of the telescope. 
        A position can be specified if an absolute change in focus is desired. 
        Use is_relative flag for relative changes in focus.
    abort()
        A function that aborts the focus changing action if the focuser is busy.
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
        self._log = mainLogger(unitnum = self.telescope.unitnum, logger_name = __name__+str(self.telescope.unitnum)).log()

    def run(self,
            position: int = None,
            is_relative : bool = False):
        """
        Excute the focus change.
        
        Parameters
        ----------
        position : int, optional
            The new focus position.
        is_relative : bool, optional
            If set to True, considers the position as a relative change. 
            If False, considers position as an absolute position. 
            Default is False.
            
        Returns
        -------
        bool
            True if the focus change action is successful, otherwise an exception is raised.

        Raises
        ------
        ConnectionException
            If the focuser of the telescope is disconnected.
        AbortionException
            If the action has been aborted.
        ActionFailedException
            If action fails due to any other reason.
        """
        self._log.info(f'[{type(self).__name__}] is triggered.')
        # Check device connection
        if self.telescope_status.focuser.lower() == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: focuser is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: focuser is disconnected.')
        
        # If not aborted, execute the action
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
         
        # Start action
        if self.telescope_status.focuser.lower() == 'idle':
            try:
                info_focuser = self.telescope.focuser.get_status()
                if is_relative:
                    position = info_focuser['position'] + position
                result_move = self.telescope.focuser.move(position = position, abort_action= self.abort_action)
            except FocusChangeFailedException:
                self._log.critical(f'[{type(self).__name__}] is failed: focuser move failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: focuser move failure.')            
            except AbortionException:
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
        elif self.telescope_status.focuser.lower() == 'busy':
            self._log.critical(f'[{type(self).__name__}] is failed: focuser is busy.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: focuser is busy.')
        else:
            self._log.critical(f'[{type(self).__name__}] is failed: focuser status error.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: focuser status error.')

        if result_move:
            self._log.info(f'[{type(self).__name__}] is finished.')
            self.shared_memory['succeeded'] = True
        return True
    
    def abort(self):
        """
        Aborts the change focus action if the focuser is busy.
        """
        self.abort_action.set()
        self.telescope.focuser.abort()
        #self.abort_action = Event()
        '''
        status_focuser = self.telescope_status.focuser.lower()
        if status_focuser == 'busy':
            self.telescope.focuser.abort()
        else:
            pass 
        '''