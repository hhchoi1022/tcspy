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
        self.is_running = False
    
    def run(self):
        """
        Execute the disconnection action.
        """
        self.telescope.register_logfile()
        self.telescope.log.info(f'=====LV1[{type(self).__name__}] is triggered.')
        self.is_running = True
        self.shared_memory['succeeded'] = False
        # disconnect devices
        devices_status = self.telescope_status.dict
        for device_name in self.telescope.devices.keys():
            if self.abort_action.is_set():
                self.abort()
            device = self.telescope.devices[device_name]
            status = devices_status[device_name]
            try:
                device.disconnect()
            except:
                pass
                        

        # check the device connection
        devices_status = self.telescope_status.dict
        self.telescope.log.info(f'[{type(self).__name__}]Checking devices connection...')
        self.telescope.log.info('='*30)
        for device_name in self.telescope.devices.keys():
            if not self.abort_action.is_set():
                device = self.telescope.devices[device_name]
                status = devices_status[device_name]
                if not status == 'disconnected':
                    self.telescope.log.critical(f'{device_name} : Connected')
                else:
                    self.telescope.log.info(f'{device_name} : Disconnected')
            else:
                self.abort()
        self.telescope.log.info('='*30)
        self.shared_memory['status'] = devices_status
        self.shared_memory['succeeded'] = True
        
        self.is_running = False
        self.telescope.log.info(f'=====LV1[{type(self).__name__}] is finished.')
        if self.shared_memory['succeeded']:
            return True
    
    def abort(self):
        self.abort_action.set()
        self.is_running = False
        self.telescope.log.warning(f'=====LV1[{type(self).__name__}] is aborted.')
        raise AbortionException(f'[{type(self).__name__}] is aborted.')
# %%
if __name__ == '__main__':
    tel1 = SingleTelescope(unitnum = 1)
    tel2 = SingleTelescope(unitnum = 2)
    Disconnect(tel1).run()
    Disconnect(tel2).run()
    

#%%