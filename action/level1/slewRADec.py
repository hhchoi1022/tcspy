#%%
from multiprocessing import Event
from multiprocessing import Manager

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.exception import *

class SlewRADec(Interface_Runnable, Interface_Abortable):
    """
    A class to perform the action of moving a telescope to a given right ascension and declination.

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
    run(ra=None, dec=None, **kwargs)
        Move the telescope to the given right ascension and declination.
    abort()
        Abort the running action.
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
            ra : float = None,
            dec : float = None,
            force_action: bool = False,
            **kwargs):
        """
        Move the telescope to the given right ascension and declination.
        
        The function returns True if the action is finished.

        Parameters
        ----------
        ra : float, optional
            The right ascension value to move the telescope to.
        dec : float, optional
            The declination value to move the telescope to.
        
        Raises
        ------
        ConnectionException
            If the telescope is disconnected.
        AbortionException
            If the action is aborted.
        ActionFailedException
            If the slew operation failed for any reason.
        
        Returns
        -------
        bool
            True if the action is finished, False otherwise.
        """
        self.telescope.register_logfile()
        self.telescope.log.info(f'=====LV1[{type(self).__name__}] is triggered.')
        self.is_running = True
        self.shared_memory['is_running'] = True
        self.shared_memory['succeeded'] = False
        # Check device connection
        mount = self.telescope.mount
        status_mount = self.telescope_status.mount.lower()

        # Check abort_action
        if self.abort_action.is_set():
            self.abort()
        
        # Start action
        if status_mount == 'disconnected':
            self.telescope.log.critical(f'=====LV1[{type(self).__name__}] is failed: mount is disconnected.')
            self.shared_memory['exception'] = 'ConnectionException'
            self.shared_memory['is_running'] = False
            self.is_running = False
            raise ConnectionException(f'[{type(self).__name__}] is failed: mount is disconnected.')
        elif status_mount == 'parked':
            self.telescope.log.critical(f'=====LV1[{type(self).__name__}] is failed: mount is parked.')
            self.shared_memory['exception'] = 'ActionFailedException'
            self.shared_memory['is_running'] = False
            self.is_running = False
            raise ActionFailedException(f'[{type(self).__name__}] is failed: mount is parked.')
        elif status_mount == 'busy':
            self.telescope.log.critical(f'=====LV1[{type(self).__name__}] is failed: mount is busy.')
            self.shared_memory['exception'] = 'ActionFailedException'
            self.shared_memory['is_running'] = False
            self.is_running = False
            raise ActionFailedException(f'[{type(self).__name__}] is failed: mount is busy.')
        else:
            try:
                result_slew = mount.slew_radec(ra = float(ra),
                                               dec = float(dec),
                                               abort_action = self.abort_action,
                                               force_action = force_action,
                                               tracking = True)
            except SlewingFailedException:
                self.telescope.log.critical(f'=====LV1[{type(self).__name__}] is failed: mount slew_altaz failure.')
                self.shared_memory['exception'] = 'ActionFailedException'
                self.shared_memory['is_running'] = False
                self.is_running = False
                raise ActionFailedException(f'[{type(self).__name__}] is failed: mount slew_altaz failure.')
            except AbortionException:
                self.abort()
        if result_slew:
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
