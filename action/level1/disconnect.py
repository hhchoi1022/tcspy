#%%
import time
from multiprocessing import Event
from multiprocessing import Manager

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.logger import mainLogger

class Disconnect(Interface_Runnable):
    
    def __init__(self, 
                 singletelescope : SingleTelescope,
                 abort_action : Event):
        """
        A class representing a disconnect action for a single telescope.

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
        run()
            Performs the action to disconnect all devices linked to the telescope.
        abort()
            A function that needs to be defined to enable abort functionality. In this class, it does nothing and should be overridden in subclasses if needed.
        """
        self.telescope = singletelescope
        self.telescope_status = TelescopeStatus(self.telescope)
        self.abort_action = abort_action
        self.shared_memory_manager = Manager()
        self.shared_memory = self.shared_memory_manager.dict()
        self.shared_memory['succeeded'] = False
        self._log = mainLogger(unitnum = self.telescope.unitnum, logger_name = __name__+str(self.telescope.unitnum)).log()
    
    def run(self):
        """
        Execute the disconnection action.
        """
        self._log.info(f'[{type(self).__name__}]" is triggered.')
        # disconnect devices
        devices_status = self.telescope_status.dict
        for device_name in self.telescope.devices.keys():
            if self.abort_action.is_set():
                self._log.warning(f'[{type(self).__name__}] is aborted.')
                return False
            device = self.telescope.devices[device_name]
            status = devices_status[device_name]
            try:
                device.disconnect()
            except:
                pass

        # check the device connection
        devices_status = self.telescope_status.dict
        self._log.info('Checking devices connection...')
        self._log.info('='*30)
        for device_name in self.telescope.devices.keys():
            if not self.abort_action.is_set():
                device = self.telescope.devices[device_name]
                status = devices_status[device_name]
                if not status == 'disconnected':
                    self._log.critical(f'{device_name} cannot be disconnected. Check the ASCOM Remote Server')
                else:
                    self._log.info(f'{device_name} : Disconnected')
            else:
                self._log.warning(f'[{type(self).__name__}] is aborted.')
        self._log.info('='*30)
        self._log.info(f'[{type(self).__name__}] is finished.')
        self.shared_memory['status'] = devices_status
        self.shared_memory['succeeded'] = True
        return True 
    
    def abort(self):
        """
        Dummy abort function. Disconnect cannot be aborted 
        """
        return 
# %%
if __name__ == '__main__':
    tel1 = SingleTelescope(unitnum = 1)
    tel2 = SingleTelescope(unitnum = 2)
    Disconnect(tel1).run()
    Disconnect(tel2).run()
    

#%%