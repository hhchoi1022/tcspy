#%%
from threading import Event

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.exception import *

class ChangeFilter(Interface_Runnable, Interface_Abortable):
    """
    A class representing a change filter action for a single telescope.

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
    run(filter_ : str)
        Performs the action to change the filter of the telescope. It does so by attempting to move the filter to a new state.
    abort()
        A function that needs to be defined to enable abort functionality. In this class, it does nothing and should be overridden in subclasses if needed.
    """
    def __init__(self, 
                 singletelescope : SingleTelescope,
                 abort_action : Event):
        self.telescope = singletelescope
        self.telescope_status = TelescopeStatus(self.telescope)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.telescope.unitnum, logger_name = __name__+str(self.telescope.unitnum)).log()

    def run(self,
            filter_ : str):
        """
        Performs the action to change the filter of the telescope.

        Parameters
        ----------
        filter_ : str
            The new filter state to which the telescope's filter wheel needs to be moved.

        Returns
        -------
        bool
            True if the action is successful, otherwise an exception is raised.
        
        Raises
        ------
        ConnectionException
            If the filter wheel of the telescope is disconnected. 
        AbortionException
            If the action has been aborted.
        ActionFailedException
            If the action fails due to any other reason.
        """
        self._log.info(f'[{type(self).__name__}] is triggered.')
        # Check device connection
        if self.telescope_status.filterwheel.lower() == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: filterwheel is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: filterwheel is disconnected.')
        
        # If not aborted, execute the action
        if self.abort_action.is_set():
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
        
        # Start action
        if self.telescope_status.filterwheel.lower() == 'idle':
            try:
                result_move = self.telescope.filterwheel.move(filter_ = filter_)
            except FilterChangeFailedException:
                self._log.critical(f'[{type(self).__name__}] is failed: filterwheel move failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: filterwheel move failure.')
                
        elif self.telescope_status.filterwheel.lower() == 'busy':
            self._log.critical(f'[{type(self).__name__}] is failed: filterwheel is busy.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: filterwheel is busy.')
        else:
            self._log.critical(f'[{type(self).__name__}] is failed: filterwheel status error.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: filterwheel status error.')

        if result_move:
            self._log.info(f'[{type(self).__name__}] is finished.')
            return True
    
    def abort(self):
        """
        A function that needs to be defined to enable abort functionality. 
        
        In this class, it does nothing and should be overridden in subclasses if needed.
        """
        return

# %%
