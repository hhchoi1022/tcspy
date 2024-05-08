#%%
from multiprocessing import Event
from multiprocessing import Manager

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.exception import *

class SlewAltAz(Interface_Runnable, Interface_Abortable):
    """
    A class to perform the action of moving a telescope to a given altitude and azimuth.

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
    run(alt=None, az=None, **kwargs)
        Move the telescope to the given altitude and azimuth.
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
        self._log = mainLogger(unitnum = self.telescope.unitnum, logger_name = __name__+str(self.telescope.unitnum)).log()
    
    def run(self,
            alt : float = None,
            az : float = None,
            force_action : bool = False,
            tracking : bool = False,
            **kwargs):
        """
        Move the telescope to the given altitude and azimuth.
        
        The function returns True if the action is finished.

        Parameters
        ----------
        alt : float, optional
            The altitude to move the telescope to.
        az : float, optional
            The azimuth to move the telescope to.
        
        Raises
        ------
        ConnectionException
            If the telescope is disconnected.
        AbortionException
            If the action is aborted.
        ActionFailedException
            If the slew operation failed for some reason.
        
        Returns
        -------
        bool
            True if the action is finished, False otherwise.
        """
        self.abort_action.clear()
        self._log.info(f'[{type(self).__name__}] is triggered.')
        # Check device connection
        mount = self.telescope.mount  
        status_mount = self.telescope_status.mount.lower()
        if status_mount == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: mount is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: mount is disconnected.')

        # Check abort_action
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
        
        # Start action
        if status_mount == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: mount is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: mount is disconnected.')
        elif status_mount == 'parked' :
            self._log.critical(f'[{type(self).__name__}] is failed: mount is parked.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: mount is parked.')
        elif status_mount == 'busy':
            self._log.critical(f'[{type(self).__name__}] is failed: mount is busy.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: mount is busy.')
        else:
            try:
                result_slew = mount.slew_altaz(alt = float(alt),
                                                   az = float(az),
                                                   abort_action = self.abort_action,
                                                   force_action = force_action,
                                                   tracking = tracking)
            except SlewingFailedException:
                self._log.critical(f'[{type(self).__name__}] is failed: mount slew_altaz failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: mount slew_altaz failure.')
            except AbortionException:
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
        
        if result_slew:
            self._log.info(f'[{type(self).__name__}] is finished.')    
            self.shared_memory['succeeded'] = True

        return True            
    
    def abort(self):
        """
        Abort the running function.
        
        This method aborts the running action if the telescope is busy. In other cases, it does nothing.
        """
        self.abort_action.set()
        #self.telescope.mount.abort()
        #status_mount = self.telescope_status.mount.lower()
        #if status_mount == 'busy':
        #    self.telescope.mount.abort()
        #else:
        #    pass 
#%%
if __name__ == '__main__':
    device = SingleTelescope(unitnum = 21)
    abort_action = Event()
    s =SlewAltAz(device, abort_action)
    #s.run(alt=40, az= 270, tracking = True)  
    from threading import Thread
    p = Thread(target = s.run, kwargs = dict(alt = 40, az = 270))