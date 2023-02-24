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
log = mainLogger(__name__).log()
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
                 device : alpaca.focuser.Focuser):
        super().__init__()
        self._checktime = float(self.config['FOCUSER_CHECKTIME'])
        self._abort_tolerance = int(self.config['FOCUSER_HALTTOL'])
        self._warn_tolerance = int(self.config['FOCUSER_WARNTOL'])
        
        if isinstance(device, alpaca.focuser.Focuser):
            self.device = device
            self.status = self.get_status()

        else:
            log.warning('Device type is not mathced to Alpaca Focuser')
            raise ValueError('Device type is not mathced to Alpaca Focuser')
    
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
        status['update_time'] = Time.now().iso
        status['jd'] = None
        status['name'] = None
        status['position'] = None
        status['maxstep'] = None
        status['stepsize'] = None
        status['temp'] = None
        status['step_abort'] = None
        status['step_warn'] = None
        status['is_abs_positioning'] = None
        status['is_moving'] = None
        status['is_tempcomp'] = None
        status['is_connected'] = None
        try:
            if self.device.Connected:
                try:
                    status['update_time'] = Time.now().iso
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
        except:
            pass
        return status
        
    @Timeout(5, 'Timeout')
    def connect(self):
        """
        Connect to the Focuser device
        """
        
        log.info('Connecting to the Focuser...')
        try:
            if not self.device.Connected:
                self.device.Connected = True
            while not self.device.Connected:
                time.sleep(self._checktime)
            if  self.device.Connected:
                log.info('Focuser connected')
        except:
            log.warning('Connection failed')
        self.status = self.get_status()
        
    
    def disconnect(self):
        """
        Disconnect to the Focuser device
        """
        
        self.device.Connected = False
        log.info('Disconnecting the Focuser...')
        while self.device.Connected:
            time.sleep(self._checktime)
        if not self.device.Connected:
            log.info('Focuser disconnected')
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
    
        status = self.get_status()
        if (position <= 0) | (position > status['maxstep']):
            logtxt = 'Set position is out of bound of this focuser (Min : %d Max : %d)'%(0, status['maxstep'])
            log.critical(logtxt)
            raise ValueError(logtxt)
        elif np.abs(position - status['position']) > status['step_abort']:
            logtxt = 'Set position is too distant from current position. Halt action. (Moving position : %d > halt tolerance : %d)'%(np.abs(position - status['position']), status['step_abort'])
            log.critical(logtxt)
            raise ValueError(logtxt)
        else:
            if np.abs(position - status['position']) > status['step_warn']:
                logtxt = 'Set position is far from current position. Be careful... (Moving position : %d > warn tolerance : %d)'%(np.abs(position - status['position']), status['step_warn'])
                log.warn(logtxt)
            log.info('Moving focuser position... (Current : %s To : %s)'%(status['position'], position))
            self.device.Move(position)
            status = self.get_status()
            while status['is_moving']:
                time.sleep(self._checktime)
                status = self.get_status()
            status = self.get_status()
            log.info('Focuser position is set (Current : %s)'%(status['position']))
        print(status)
        
    def abort(self):
        """
        Abort the movement of the Focuser device
        """
    
        self.device.Halt()
        log.warning('Focuser aborted')
        
        
        
# %% Test
if __name__ == '__main__':
    Focus = Focuser('127.0.0.1:32323', 0)
    F = mainFocuser(Focus)
    #%%
    F.move(19000)

# %%
