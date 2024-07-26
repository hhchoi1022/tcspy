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
    ----------
    unitnum : int
        The unit number.

    Attributes
    ----------
    device : alpaca.focuser.Focuser
        The Focuser device to control.
    status : dict
        A dictionary containing the current status of the Focuser device.

    Methods
    -------
    get_status() -> dict
        Get the status of the Focuser device.
    connect() -> None
        Connect to the Focuser device.
    disconnect() -> None
        Disconnect from the Focuser device.
    move(position: int, abort_action: Event) -> None
        Move the Focuser device to the specified position.
    fans_on() -> bool
        Turn on the fans (not implemented in Alpaca Telescope).
    fans_off() -> bool
        Turn off the fans (not implemented in Alpaca Telescope).
    autofocus_start(abort_action: Event) -> bool
        Start autofocus (not implemented in Alpaca Telescope).
    abort() -> None
        Abort the movement of the Focuser device.
    """
    
    def __init__(self,
                 unitnum : int,
                 **kwargs):
        
        super().__init__(unitnum = unitnum)
        self.device = Focuser(f"{self.config['FOCUSER_HOSTIP']}:{self.config['FOCUSER_PORTNUM']}",self.config['FOCUSER_DEVICENUM'])
        self.status = self.get_status()
        self._log = mainLogger(unitnum = unitnum, logger_name = __name__+str(unitnum)).log()
    
    def get_status(self) -> dict:
        """
        Get the status of the Focuser device.

        Returns
        -------
        status : dict
            A dictionary containing the current status of the Focuser device.
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
                time.sleep(float(self.config['FOCUSER_CHECKTIME']))
            while not self.device.Connected:
                time.sleep(float(self.config['FOCUSER_CHECKTIME']))
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
                time.sleep(float(self.config['FOCUSER_CHECKTIME']))
            while self.device.Connected:
                time.sleep(float(self.config['FOCUSER_CHECKTIME']))
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
        Move the Focuser device to the specified position.

        Parameters
        ----------
        position : int
            The position to move the device to.
        abort_action : threading.Event
            An event object used to abort the movement process.
        """
        maxstep = self.device.MaxStep
        if (position <= 1000) | (position > maxstep):
            self._log.critical('Set position is out of bound of this focuser (Min : %d Max : %d)'%(1000, maxstep))
            raise FocusChangeFailedException('Set position is out of bound of this focuser (Min : %d Max : %d)'%(1000, maxstep))
        else:
            current_position = self.device.Position
            self._log.info('Moving focuser position... (Current : %s To : %s)'%(current_position, position))
            self.device.Move(position)
            time.sleep(float(self.config['FOCUSER_CHECKTIME']))
            while not np.abs(current_position - position) < 10:
                current_position = self.device.Position
                time.sleep(float(self.config['FOCUSER_CHECKTIME']))
                if abort_action.is_set():
                    self.abort()
                    self._log.warning('Focuser moving is aborted')
                    raise AbortionException('Focuser moving is aborted')
            current_position = self.device.Position
            self._log.info('Focuser position is set (Current : %s)'%(position))
        return True
    
    def fans_on(self):
        """
        Turn on the fans (not implemented in Alpaca Telescope).
        """
        print('Fans operation is not implemented in Alpaca Telescope')
        return True
    
    def fans_off(self):
        """
        Turn off the fans (not implemented in Alpaca Telescope).
        """
        print('Fans operation is not implemented in Alpaca Telescope')
        return True
    
    def autofocus_start(self, abort_action : Event):
        """
        Start autofocus (not implemented in Alpaca Telescope).

        Parameters
        ----------
        abort_action : threading.Event
            An event object used to abort the autofocus process.
        """
        print('Autofocus is not implemented in Alpaca Telescope')
        return True, 10000
    
    def autofocus_stop(self, abort_action : Event):
        """
        Stop autofocus (not implemented in Alpaca Telescope).

        Parameters
        ----------
        abort_action : threading.Event
            An event object used to abort the autofocus process.
        """
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
