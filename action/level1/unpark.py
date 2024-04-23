#%%
from multiprocessing import Event
from multiprocessing import Manager

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.utils.logger import mainLogger
from tcspy.interfaces import *
from tcspy.utils.exception import *

class Unpark(Interface_Runnable, Interface_Abortable):
    """
    A class to perform the action of unparking a telescope.

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
        Unpark the telescope.
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
        self._log = mainLogger(unitnum = self.telescope.unitnum, logger_name = __name__+str(self.telescope.unitnum)).log()

    def run(self):
        """
        Unpark the telescope.

        Raises
        ------
        ConnectionException
            If the telescope is disconnected.
        ActionFailedException
            If the action of unparking failed.
        
        Returns
        -------
        bool
            True if the action is finished, False otherwise.
        """
        # Check device connection
        self._log.info(f'[{type(self).__name__}] is triggered.')
        status_mount = self.telescope_status.mount.lower()
        if status_mount == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: mount is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: mount is disconnected.')

        # Start action
        if status_mount == 'busy':
            self._log.critical(f'[{type(self).__name__}] is failed: mount is busy.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: mount is busy.')
        else:
            try:
                result_unpark = self.telescope.mount.unpark()
            except ParkingFailedException:
                self._log.info(f'[{type(self).__name__}] is finished.')
                self._log.critical(f'[{type(self).__name__}] is failed')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: mount unpark failure.')
                
        if result_unpark:
            self._log.info(f'[{type(self).__name__}] is finished.')
            self.shared_memory['succeeded'] = True
        return True
    
    def abort(self):
        """
        Dummy abort function
        """
        return

#%%
if __name__ == '__main__':
    device = SingleTelescope(unitnum = 2)
    abort_action = Event()
    s =Unpark(device, abort_action= abort_action)
    s.run()

# %%
