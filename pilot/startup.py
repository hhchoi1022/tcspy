

#%%
from threading import Event
from typing import List, Union
import time
import threading


from tcspy.configuration import mainConfig
from tcspy.action.level1 import *
from tcspy.devices import IntegratedDevice
from tcspy.devices import MultiTelescopes
from tcspy.action import MultiAction
from tcspy.utils.exception import *

#%%

class StartUp(mainConfig):
    
    def __init__(self,
                 MultiTelescopes,
                 abort_action : Event,
                 ):
        super().__init__()
        self.multitelescopes = MultiTelescopes
        self.devices = MultiTelescopes.devices
        self.log = MultiTelescopes.log
        self.abort_action = abort_action
    
    def run(self):
        startup_thread = threading.Thread(target=self.process)
        startup_thread.start()
    
    def process(self):
        
        # Connect
        params_connect = []
        for IDevice_name, IDevice in self.devices.items():
            self.log[IDevice_name].info(f'[{type(self).__name__}] is triggered.')
            params_connect.append(dict())
        multi_connect = MultiAction(array_telescope= self.devices.values(), array_kwargs= params_connect, function = Connect, abort_action = self.abort_action)    
        multi_connect.run()
        result_multi_connect = multi_connect.get_results().copy()
        
        timeout = 10
        start_time = time.time()
        while all(key in result_multi_connect for key in self.devices) == False:
            if time.time() - start_time > timeout:
                print("Timeout")
                break
            time.sleep(1)
            result_multi_connect = multi_connect.get_results().copy()
            if self.abort_action.is_set():
                self.abort()
                for IDevice_name, IDevice in self.devices.items():
                    self.log[IDevice_name].warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
        result_multi_connect = multi_connect.get_results().copy()
        no_response_device = set(self.devices.keys())-set(result_multi_connect.keys())
        action_failed_device = set([key for key, value in result_multi_connect.items() if value == False])
        device_to_remove = no_response_device | action_failed_device
        if len(device_to_remove) > 0:
            for IDevice_name in device_to_remove:
                self.log[IDevice_name].critical(f'[{type(self).__name__}] is failed: Connection failure.')
                self.multitelescopes.remove(IDevice_name)
        
        # Check abort_action
        if self.abort_action.is_set():
            self.abort()
            for IDevice_name, IDevice in self.devices.items():
                self.log[IDevice_name].warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')
        
        # Telescope slewing
        params_slew = []
        for IDevice_name, IDevice in self.devices.items():
            params_slew.append(dict(alt = 50,#self.config['STARTUP_ALT'],
                                    az = 0))#self.config['STARTUP_AZ']))
        multi_slew = MultiAction(array_telescope= self.devices.values(), array_kwargs= params_slew, function = SlewAltAz, abort_action = self.abort_action)
        multi_slew.run()
        result_multi_slew = multi_slew.get_results().copy()
        timeout = 60
        start_time = time.time()
        while all(key in result_multi_slew for key in self.devices) == False:
            if time.time() - start_time > timeout:
                print("Timeout")
                break
            time.sleep(1)
            result_multi_slew = multi_slew.get_results().copy()
            if self.abort_action.is_set():
                self.abort()
                for IDevice_name, IDevice in self.devices.items():
                    self.log[IDevice_name].warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
        no_response_device = set(self.devices.keys())-set(result_multi_slew.keys())
        action_failed_device = set([key for key, value in result_multi_slew.items() if value == False])
        device_to_remove = no_response_device | action_failed_device
        if len(device_to_remove) > 0:
            for IDevice_name in device_to_remove:
                self.log[IDevice_name].critical(f'[{type(self).__name__}] is failed: Slewing failure.')
                self.multitelescopes.remove(IDevice_name)

        # Check abort_action
        if self.abort_action.is_set():
            self.abort()
            for IDevice_name, IDevice in self.devices.items():
                self.log[IDevice_name].warning(f'[{type(self).__name__}] is aborted.')
            raise AbortionException(f'[{type(self).__name__}] is aborted.')

        # Camera cooling 
        params_cool = []
        for IDevice_name, IDevice in self.devices.items():
            params_cool.append(dict(settemperature = self.config['STARTUP_CCDTEMP'],
                                    tolerance = self.config['STARTUP_CCDTEMP_TOLERANCE']))
        multi_cool = MultiAction(array_telescope= self.devices.values(), array_kwargs= params_cool, function = Cool, abort_action = self.abort_action)
        multi_cool.run()
        result_multi_cool = multi_cool.get_results().copy()
        timeout = 600
        start_time = time.time()
        while all(key in result_multi_cool for key in self.devices) == False:
            if time.time() - start_time > timeout:
                print("Timeout")
                break
            time.sleep(1)
            result_multi_cool = multi_cool.get_results().copy()
            if self.abort_action.is_set():
                self.abort()
                for IDevice_name, IDevice in self.devices.items():
                    self.log[IDevice_name].warning(f'[{type(self).__name__}] is aborted.')
                raise AbortionException(f'[{type(self).__name__}] is aborted.')
        no_response_device = set(self.devices.keys())-set(result_multi_cool.keys())
        action_failed_device = set([key for key, value in result_multi_cool.items() if value == False])
        device_to_remove = no_response_device | action_failed_device
        if len(device_to_remove) > 0:
            for IDevice_name in device_to_remove:
                self.log[IDevice_name].critical(f'[{type(self).__name__}] is failed: Cooling failure.')
                self.multitelescopes.remove(IDevice_name)
        
        for IDevice_name, IDevice in self.devices.items():
            self.log[IDevice_name].info(f'[{type(self).__name__}] is finished.')
    
    def abort(self):
        self.abort_action.set()
        for IDevice_name, IDevice in self.devices.items():
            self.log[IDevice_name].warning(f'[{type(self).__name__}] is aborted.')
    
    

# %%
if __name__ == '__main__':
    
    M = MultiTelescopes([IntegratedDevice(1),IntegratedDevice(2)])
    abort_action = Event()
    S = StartUp(M, abort_action = abort_action)
    
    
# %%
