#%%
from astropy.io import ascii
from astropy.time import Time
import time
from alpaca.safetymonitor import SafetyMonitor

from tcspy.utils.logger import mainLogger
from tcspy.utils import Timeout
from tcspy.configuration import mainConfig
# %%
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
                 unitnum : int,
                 **kwargs):
        
        super().__init__(unitnum = unitnum)
        self._log = mainLogger(unitnum = unitnum, logger_name = __name__+str(unitnum)).log()
        self._checktime = float(self.config['SAFEMONITOR_CHECKTIME'])
        self.device = SafetyMonitor(f"{self.config['SAFEMONITOR_HOSTIP']}:{self.config['SAFEMONITOR_PORTNUM']}",self.config['SAFEMONITOR_DEVICENUM'])
        self.status = self.get_status()
        
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
        status['update_time'] = Time.now().isot
        status['jd'] = round(Time.now().jd, 6)
        status['name'] = None
        status['is_connected'] = False
        status['is_safe'] = None
        if self.device.Connected:    
            try:
                status['update_time'] = Time.now().isot
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
        
        self._log.info('Connecting to the SafetyMonitor device...')
        try:
            if not self.device.Connected:
                self.device.Connected = True
            time.sleep(self._checktime)
            while not self.device.Connected:
                time.sleep(self._checktime)
            if  self.device.Connected:
                self._log.info('SafetyMonitor is connected')
            return True
        except:
            self._log.warning('Connection failed')
            return False
    
    @Timeout(5, 'Timeout')
    def disconnect(self):
        """
        Disconnect from the SafetyMonitor device
        """
        
        self._log.info('Disconnecting SafetyMonitor device...')
        try:
            if self.device.Connected:
                self.device.Connected = False
                time.sleep(self._checktime)
            while self.device.Connected:
                time.sleep(self._checktime)
            if not self.device.Connected:
                self._log.info('SafetyMonitor is disconnected')
        except:
            self._log.warning('Disconnect failed')
            return False
        return True
# %%
if __name__ == '__main__':
    safe = mainSafetyMonitor(unitnum = 4)
    safe.connect()
    safe.get_status()
    safe.disconnect()

# %%
