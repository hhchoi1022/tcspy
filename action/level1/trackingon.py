#%%
from threading import Event

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.exception import *

class TrackingOn(Interface_Runnable, Interface_Abortable):
    """
    A class to perform the action of turning on the tracking of a telescope.

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
    run()
        Turn on the tracking of the telescope.
    abort()
        This method does nothing but should be overridden in the subclasses if needed.
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
        Turn on the tracking of the telescope.

        Raises
        ------
        ConnectionException
            If the telescope is disconnected.
        ActionFailedException
            If the action of turning on tracking failed.
        
        Returns
        -------
        bool
            True if the action is finished, False otherwise.
        """
        self._log.info(f'[{type(self).__name__}] is triggered.')
        # Check device connection
        if self.telescope_status.mount.lower() == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: mount is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: mount is disconnected.')
        
        # Start action
        status_mount = self.telescope_status.mount.lower()
        if status_mount == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: mount is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: mount is disconnected.')
        elif status_mount == 'parked' :
            self._log.critical(f'[{type(self).__name__}] is failed: mount is parked.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: mount is parked.')
        else:
            try:
                result_tracking = self.telescope.mount.tracking_on()
            except TrackingFailedException:
                self._log.critical(f'[{type(self).__name__}] is failed: mount siderialtracking failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: mount siderialtracking failure.')
                
        if result_tracking:
            self._log.info(f'[{type(self).__name__}] is finished.')
        return True
        
    def abort(self):
        """
        Dummy abort function
        """
        return 