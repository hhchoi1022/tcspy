#%%
# Other modules
from astropy.io import ascii
import time
from astropy.time import Time
import numpy as np
# Alpaca modules
from alpaca.focuser import Focuser
import alpaca
#TCSpy modules
from tcspy.utils import mainLogger
from tcspy.utils import Timeout
from tcspy.configuration import mainConfig

# %%
class mainFocuser(mainConfig):
    """
    A class for controlling a Focuser device.

    Parameters
    ==========
    1. device : alpaca.focuser.Focuser
        The Focuser device to control.

    Methods
    =======
    1. get_status() -> dict
        Get the status of the Focuser device.
    2. connect() -> None
        Connect to the Focuser device.
    3. disconnect() -> None
        Disconnect from the Focuser device.
    4. move(position: int) -> None
        Move the Focuser device to the specified position.
    5. abort() -> None
        Abort the movement of the Focuser device.
    """
    
    def __init__(self,
                 unitnum : int,
                 **kwargs):
        
        super().__init__(unitnum = unitnum)
        self._log = mainLogger(unitnum = unitnum, logger_name = __name__+str(unitnum)).log()
        self._checktime = float(self.config['FOCUSER_CHECKTIME'])
        self._abort_tolerance = int(self.config['FOCUSER_HALTTOL'])
        self._warn_tolerance = int(self.config['FOCUSER_WARNTOL'])
        self.device = Focuser(f"{self.config['FOCUSER_HOSTIP']}:{self.config['FOCUSER_PORTNUM']}",self.config['FOCUSER_DEVICENUM'])
        self.status = self.get_status()
    
    def get_status(self) -> dict:
        """
        Get the status of the Focuser device

        Return
        ======
        1. status : dict
            A dictionary containing the current status of the Focuser device.
            Keys:
                - 'name': Name of the device
                - 'position': Current position of the device
                - 'maxstep': Maximum position of the device
                - 'stepsize': Step size of the device
                - 'temp': Temperature of the device
                - 'step_abort': Movement distance threshold for halting action
                - 'step_warn': Movement distance threshold for warning
                - 'is_abs_positioning': Flag indicating if the device is using absolute positioning
                - 'is_moving': Flag indicating if the device is currently moving
                - 'is_tempcomp': Flag indicating if the device is using temperature compensation
                - 'is_connected': Flag indicating if the device is connected
        """
        
        status = dict()
        status['update_time'] = Time.now().isot
        status['jd'] = round(Time.now().jd,6)
        status['is_connected'] = False
        status['name'] = None
        status['position'] = None
        status['is_moving'] = None
        status['maxstep'] = None
        status['stepsize'] = None
        status['temp'] = None
        status['step_abort'] = None
        status['step_warn'] = None
        status['is_abs_positioning'] = None
        status['is_tempcomp'] = None
        
        if self.device.Connected:
            try:
                status['update_time'] = Time.now().isot
            except:
                pass
            try:
                status['jd'] = round(Time.now().jd,5)
            except:
                pass
            try:
                status['name'] = self.device.Name
            except:
                pass
            try:
                status['position'] = self.device.Position
            except:
                pass
            try:
                status['maxstep'] = self.device.MaxStep
            except:
                pass
            try:
                status['stepsize'] = self.device.StepSize
            except:
                pass
            try:
                status['temp'] = self.device.Temperature
            except:
                pass
            try:
                status['step_abort'] = self._abort_tolerance
            except:
                pass
            try:
                status['step_warn'] = self._warn_tolerance
            except:
                pass
            try:
                status['is_abs_positioning'] = self.device.Absolute
            except:
                pass
            try:
                status['is_moving'] = self.device.IsMoving
            except:
                pass
            try:
                status['is_tempcomp'] = self.device.TempComp
            except:
                pass
            try:
                status['is_connected'] = self.device.Connected
            except:
                pass

        return status
        
    @Timeout(5, 'Timeout')
    def connect(self):
        """
        Connect to the Focuser device
        """
        
        self._log.info('Connecting to the Focuser...')
        try:
            if not self.device.Connected:
                self.device.Connected = True
            while not self.device.Connected:
                time.sleep(self._checktime)
            if  self.device.Connected:
                self._log.info('Focuser connected')
        except:
            self._log.warning('Connection failed')
        self.status = self.get_status()
        
    
    def disconnect(self):
        """
        Disconnect to the Focuser device
        """
        
        self.device.Connected = False
        self._log.info('Disconnecting the Focuser...')
        while self.device.Connected:
            time.sleep(self._checktime)
        if not self.device.Connected:
            self._log.info('Focuser disconnected')
        self.status = self.get_status()
            
    def move(self,
             position : int):
        """
        Move the Focuser device to the specified position

        Parameters
        ==========
        1. position : int
            The position to move the device to
        """
    
        self.status = self.get_status()
        if (position <= 0) | (position > self.status['maxstep']):
            logtxt = 'Set position is out of bound of this focuser (Min : %d Max : %d)'%(0, self.status['maxstep'])
            self._log.critical(logtxt)
            raise ValueError(logtxt)
        elif np.abs(position - self.status['position']) > self.status['step_abort']:
            logtxt = 'Set position is too distant from current position. Halt action. (Moving position : %d > halt tolerance : %d)'%(np.abs(position - self.status['position']), self.status['step_abort'])
            self._log.critical(logtxt)
            raise ValueError(logtxt)
        else:
            if np.abs(position - self.status['position']) > self.status['step_warn']:
                logtxt = 'Set position is far from current position. Be careful... (Moving position : %d > warn tolerance : %d)'%(np.abs(position - self.status['position']), self.status['step_warn'])
                self._log.warn(logtxt)
            self._log.info('Moving focuser position... (Current : %s To : %s)'%(self.status['position'], position))
            self.device.Move(position)
            time.sleep(3*self._checktime)
            while self.device.IsMoving:
                time.sleep(self._checktime)
            self._log.info('Focuser position is set (Current : %s)'%(self.status['position']))
        self.status = self.get_status()
        
    def abort(self):
        """
        Abort the movement of the Focuser device
        """
    
        self.device.Halt()
        self.status = self.get_status()
        self._log.warning('Focuser aborted')
        
        
        
# %% Test
if __name__ == '__main__':
    #Focus = Focuser('192.168.0.4:11111', 0)
    F = mainFocuser(unitnum = 1)
    F.connect()
    F.move(19000)
    F.disconnect()

# %%
