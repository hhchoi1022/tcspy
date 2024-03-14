#%%
from astropy.io import ascii
import time
from astropy.time import Time
import numpy as np
from threading import Event

from alpaca.focuser import Focuser

from tcspy.utils.logger import mainLogger
from tcspy.utils import Timeout
from tcspy.configuration import mainConfig
from tcspy.utils.exception import *

# %%
class mainFocuser_Alpaca(mainConfig):
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
                time.sleep(self._checktime)
            while not self.device.Connected:
                time.sleep(self._checktime)
            if  self.device.Connected:
                self._log.info('Focuser connected')
        except:
            self._log.warning('Connection failed')
            raise ConnectionException('Connection failed')
        return True
        
    @Timeout(5, 'Timeout')
    def disconnect(self):
        """
        Disconnect to the Focuser device
        """
        
        self._log.info('Disconnecting focuser...')
        try:
            if self.device.Connected:
                self.device.Connected = False
                time.sleep(self._checktime)
            while self.device.Connected:
                time.sleep(self._checktime)
            if not self.device.Connected:
                self._log.info('Focuser disconnected')
        except:
            self._log.warning('Disconnect failed')
            return ConnectionException('Disconnect failed')
        return True
            
    def move(self,
             position : int,
             abort_action : Event):
        """
        Move the Focuser device to the specified position

        Parameters
        ==========
        1. position : int
            The position to move the device to
        """
    
        maxstep = self.device.MaxStep
        if (position <= 1000) | (position > maxstep):
            self._log.critical('Set position is out of bound of this focuser (Min : %d Max : %d)'%(1000, maxstep))
            raise FocusChangeFailedException('Set position is out of bound of this focuser (Min : %d Max : %d)'%(1000, maxstep))
        else:
            current_position = self.device.Position
            self._log.info('Moving focuser position... (Current : %s To : %s)'%(current_position, position))
            self.device.Move(position)
            time.sleep(self._checktime)
            while not np.abs(current_position - position) < 10:
                current_position = self.device.Position
                time.sleep(self._checktime)
                if abort_action.is_set():
                    self._log.warning('Focuser moving is aborted')
                    raise AbortionException('Focuser moving is aborted')
            current_position = self.device.Position
            self._log.info('Focuser position is set (Current : %s)'%(position))
        return True
    
    def fans_on(self):
        print('Fans operation is not implemented in Alpaca Telescope')
        return True
    
    def fans_off(self):
        print('Fans operation is not implemented in Alpaca Telescope')
        return True
    
    def autofocus_start(self, abort_action : Event):
        print('Autofocus is not implemented in Alpaca Telescope')
        return True
    
    def autofocus_start(self, abort_action : Event):
        print('Autofocus is not implemented in Alpaca Telescope')
        return True
        
    def abort(self):
        """
        Abort the movement of the Focuser device
        """
        self.device.Halt()   

        
        
# %% Test
if __name__ == '__main__':
    #Focus = Focuser('192.168.0.4:11111', 0)
    F = mainFocuser(unitnum = 2)
    F.connect()
    F.move(8000, Event())
# %%
