#%%
from multiprocessing import Event
from multiprocessing import Manager

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.exception import * 

class Park(Interface_Runnable, Interface_Abortable):
    """
    A class representing a Park action for a telescope.

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
        Performs the action to park the telescope.
    abort()
        Sends an abort command to the mount if it is busy.
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
        self.is_running = False

    def run(self):
        """
        Performs the action to park the telescope.

        Raises
        ------
        ConnectionException
            If the mount is disconnected.
        AbortionException
            If the operation is aborted.
        ActionFailedException
            If there is an error during the park operation.
        """
        self._log.info(f'=====LV1[{type(self).__name__}] is triggered.')
        self.is_running = True
        self.shared_memory['succeeded'] = False
        # Check device connection
        mount = self.telescope.mount
        status_mount = self.telescope_status.mount.lower()

        # If not aborted, execute the action
        if self.abort_action.is_set():
            self.abort()

        # Start action
        if status_mount == 'disconnected':
            self.is_running = False
            self._log.critical(f'=====LV1[{type(self).__name__}] is failed: mount is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: mount is disconnected.')
        if status_mount == 'busy':
            self.is_running = False
            self._log.critical(f'=====LV1[{type(self).__name__}] is failed: mount is busy.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: mount is busy.')
        else:
            try:
                self._log.info(f'[{type(self).__name__}] Move to the park position (Alt={self.telescope.config["MOUNT_PARKALT"]}, Az={self.telescope.config["MOUNT_PARKAZ"]})')
                result_park = mount.park(abort_action = self.abort_action)
            except ParkingFailedException:
                self.is_running = False
                self._log.critical(f'=====LV1[{type(self).__name__}] is failed')
                ActionFailedException(f'[{type(self).__name__}] is failed: mount park failure.')
            except AbortionException:
                self.abort()
        if result_park:
            self.shared_memory['succeeded'] = True
            
        self.is_running = False
        self._log.info(f'=====LV1[{type(self).__name__}] is finished.')            
        if self.shared_memory['succeeded']:
            return True    
        
    def abort(self):
        self.abort_action.set()
        self.is_running = False
        self._log.warning(f'=====LV1[{type(self).__name__}] is aborted.')
        raise AbortionException(f'[{type(self).__name__}] is aborted.')

#%%
if __name__ == '__main__':
    device = SingleTelescope(unitnum = 8)
    abort_action = Event()
    s =Park(device, abort_action= abort_action)
    s.run()

# %%
