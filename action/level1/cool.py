#%%
from threading import Event

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger
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
        self._log = mainLogger(unitnum = self.telescope.unitnum, logger_name = __name__+str(self.telescope.unitnum)).log()

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
        self._log.info(f'[{type(self).__name__}] is triggered.')
        # Check device connection
        if self.telescope_status.camera.lower() == 'disconnected':
            self._log.critical(f'[{type(self).__name__}] is failed: camera is disconnected.')
            raise ConnectionException(f'[{type(self).__name__}] is failed: camera is disconnected.')
        
        # If not aborted, execute the action
        if self.abort_action.is_set():
            self.abort()
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
        # Start action
        try:
            result_cool = self.telescope.camera.cool(settemperature = settemperature, 
                                                   tolerance = tolerance,
                                                   abort_action = self.abort_action)
        except CoolingFailedException:
            self._log.critical(f'[{type(self).__name__}] is failed: camera cool failure.')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: camera cool failure.')
        except AbortionException:
            self._log.warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
            
        if result_cool:
            self._log.info(f'[{type(self).__name__}] is finished.')
        return True
    
    def abort(self):
        """
        Aborts the cooling action if the camera is already cooling.
        """
        if self.telescope.camera.device.CoolerOn:
            if self.telescope.camera.device.CCDTemperature < self.telescope.camera.device.CCDTemperature -20:
                self._log.critical(f'Turning off when the CCD Temperature below ambient may lead to damage to the sensor.')
                self.telescope.camera.cooler_off()
            else:
                self.telescope.camera.cooler_off()
        else:
            pass