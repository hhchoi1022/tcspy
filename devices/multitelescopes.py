#%%
from typing import List
from tcspy.devices import IntegratedDevice
from tcspy.devices import DeviceStatus
from tcspy.utils.logger import mainLogger

#%%

class MultiTelescopes:
    
    def __init__(self, 
                 array_IntegratedDevice : List[IntegratedDevice]):
        self._devices_list = array_IntegratedDevice
        self.devices = self._get_telescopes()
        self.log = self._get_all_logs()
    
    def _get_telescopes(self):
        IDevices_dict = dict()
        for IDevice in self._devices_list:
            IDevice_name = IDevice.name
            IDevices_dict[IDevice_name] = IDevice
        return IDevices_dict

    def _get_all_logs(self):
        all_logs_dict = dict()
        for IDevice in self._devices_list:
            IDevice_name = IDevice.name
            log = mainLogger(unitnum = IDevice.unitnum, logger_name = __name__+str(IDevice.unitnum)).log()
            all_logs_dict[IDevice_name] = log
        return all_logs_dict
    
    def add(self,
            IntegratedDevice : IntegratedDevice):
        IDevice_name = IntegratedDevice.name
        log = mainLogger(unitnum = IntegratedDevice.unitnum, logger_name = __name__+str(IntegratedDevice.unitnum)).log()
        self.devices[IDevice_name] = IntegratedDevice
        self.log[IDevice_name] = log
    
    def remove(self,
               IDevice_name):
        self.devices.pop(IDevice_name)
        self.log.pop[IDevice_name]

    @property
    def status(self):
        IDevices_status_dict = dict()
        for IDevice in self._devices_list:
            name_IDevice = IDevice.name
            IDevices_status_dict[name_IDevice] = DeviceStatus(IDevice).dict
        return IDevices_status_dict
    