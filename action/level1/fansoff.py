#%%
from threading import Event

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.exception import *

class FansOff(Interface_Runnable, Interface_Abortable):
    """
    A class representing a FansOff action for a telescope.

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
        Performs the action to turn off the fans of the telescope.
    abort()
        A function to be defined to enable abort functionality. In this class, it does nothing and should be overridden in subclasses if needed.
    """

    def __init__(self, 
                 singletelescope : SingleTelescope,
                 abort_action : Event):
        self.telescope = singletelescope
        self.telescope_status = TelescopeStatus(self.telescope)
        self.abort_action = abort_action
        self._log = mainLogger(unitnum = self.telescope.unitnum, logger_name = __name__+str(self.telescope.unitnum)).log()

    def run(self):
        """
        Performs the action to turn off the fans of the telescope.

        Raises
        ------
        ConnectionException
            If the focuser is disconnected.
        AbortionException
            If the operation is aborted.
        ActionFailedException
            If there is an error during the fan operation.
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
        try:
            result_fansoff = self.telescope.focuser.fans_off()
        except FocusFansFailedException:
            self._log.critical(f'[{type(self).__name__}] is failed: fan operation failure.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: fan operation failure.')          

        if result_fansoff:
            self._log.info(f'[{type(self).__name__}] is finished.')
        return True
    
    def abort(self):
        """
        Dummy abort function
        """
        pass 
