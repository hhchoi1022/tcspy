#%%
from alpaca.safetymonitor import SafetyMonitor

from tcspy.utils import mainLogger
from tcspy.utils import Timeout
from tcspy.configuration import mainConfig

from astropy.io import ascii
from astropy.time import Time
import time
# %%
log = mainLogger(__name__).log()
class mainSafetyMonitor(mainConfig):
    """
    A class that provides a wrapper for the Alpaca SafetyMonitor device.

    Parameters
    ==========
    1. device : SafetyMonitor
        The SafetyMonitor device object to be used.
    
    Methods
    =======
    1. get_status() -> dict
        Get the status of the SafetyMonitor device.
        Returns a dictionary containing the current status of the device.
    2. connect()
        Connect to the SafetyMonitor device.
    3. disconnect()
        Disconnect from the SafetyMonitor device.
    """
    
    def __init__(self,
                 device : SafetyMonitor):
        super().__init__()
        if isinstance(device, SafetyMonitor):
            self.device = device
            self.status = self.get_status()
        else:
            log.warning('Device type is not mathced to Alpaca SafetyMonitor device')
            raise ValueError('Device type is not mathced to Alpaca SafetyMonitor device')
        self._checktime = float(self.config['SAFEMONITOR_CHECKTIME'])
        
    def get_status(self) -> dict:
        """
        Get the status of the SafetyMonitor device

        Return
        ======
        1. status : dict
            A dictionary containing the current status of the SafetyMonitor device.
            Keys:
                - 'update_time': Time stamp of the status update in ISO format
                - 'jd': Julian date of the status update, rounded to six decimal places
                - 'name': Name of the device
                - 'is_connected': Flag indicating if the device is connected
                - 'is_safe': Flag indicating if the weather is safe
        """
        
        
        status = dict()
        status['update_time'] = Time.now().iso
        status['jd'] = round(Time.now().jd, 6)
        status['name'] = None
        status['is_connected'] = None
        status['is_safe'] = None
        if self.device.Connected:     
            try:
                status['update_time'] = Time.now().iso
            except:
                pass
            try:
                status['name'] = self.device.Name
            except:
                pass
            try:
                status['is_connected'] = self.device.Connected
            except:
                pass
            try:
                status['is_safe'] =self.device.IsSafe
            except:
                pass
        return status
    
    @Timeout(5, 'Timeout')
    def connect(self):
        """
        Connect to the SafetyMonitor device
        """
        
        log.info('Connecting to the SafetyMonitor device...')
        try:
            if not self.device.Connected:
                self.device.Connected = True
                while not self.device.Connected:
                    time.sleep(self._checktime)
                if  self.device.Connected:
                    log.info('SafetyMonitor device connected')
        except :
            log.warning('Connection failed')
    
    def disconnect(self):
        """
        Disconnect from the SafetyMonitor device
        """
        
        if self.device.Connected:
            self.device.Connected = False
            log.info('Disconnecting the SafetyMonitor device...')
            while self.device.Connected:
                time.sleep(self._checktime)
            if not self.device.Connected:
                log.info('Weather SafetyMonitor disconnected')
# %%
if __name__ == '__main__':
    smonitor = SafetyMonitor('127.0.0.1:32323', 0)
    safe = mainSafetyMonitor(device= smonitor)
    safe.connect()
    safe.get_status()

# %%
