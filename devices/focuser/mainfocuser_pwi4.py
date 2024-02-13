#%%
from astropy.io import ascii
import time
from astropy.time import Time
import numpy as np
from threading import Event

from tcspy.devices import PWI4

from tcspy.utils.logger import mainLogger
from tcspy.utils import Timeout
from tcspy.configuration import mainConfig
from tcspy.utils.exception import *

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
        self.device = PWI4(self.config['TELESCOPE_HOSTIP'], self.config['TELESCOPE_PORTNUM'])
        self.status = self.get_status()
        
    def get_status(self) -> dict:
        status = dict()
        status['update_time'] = Time.now().isot
        status['jd'] = round(Time.now().jd,6)
        status['position'] = None
        status['is_connected'] = False
        status['is_enabled'] = None
        status['is_moving'] = None
        status['is_autofocusing'] = None
        status['is_autofocus_success'] = None
        status['is_autofocus_bestposition'] = None
        status['is_autofocus_tolerance'] = None
        
        try:
            if self.PWI_status.mount.is_connected:
                PWI_status = self.PWI_status
                status['update_time'] = PWI_status.response.timestamp_utc
                status['jd'] = "{:.6f}".format(PWI_status.mount.julian_date)
                status['position'] = PWI_status.focuser.position
                status['is_connected'] = PWI_status.focuser.is_connected
                status['is_enabled'] = PWI_status.focuser.is_enabled
                status['is_moving'] = PWI_status.focuser.is_moving
                status['is_autofocusing'] = PWI_status.autofocus.is_running
                status['is_autofocus_success'] = PWI_status.autofocus.success
                status['autofocus_bestposition'] = PWI_status.autofocus.best_position
                status['autofocus_tolerance'] = PWI_status.autofocus.tolerance
        except:
            pass
        return status

    @property
    def PWI_status(self):
        return self.device.status()
    
    @Timeout(5, 'Timeout')
    def connect(self):
        """
        Connect to the telescope.
        """
        
        self._log.info('Connecting to the focuser...')
        status = self.get_status()
        try:
            if not status['is_connected']:
                self.device.focuser_connect()
            time.sleep(self._checktime)
            while not status['is_connected']:
                time.sleep(self._checktime)
                status = self.get_status()
            if status['is_connected']:
                self._log.info('Focuser connected')
        except:
            self._log.critical('Connection failed')
            raise ConnectionException('Connection failed')
        return True
        
    @Timeout(5, 'Timeout')
    def disconnect(self):
        """
        Disconnect from the focuser.
        """
        
        self._log.info('Disconnecting to the focuser...')
        status = self.get_status()
        try:
            if status['is_connected']:
                self.device.focuser_disconnect()
            time.sleep(self._checktime)
            while status['is_connected']:
                time.sleep(self._checktime)
                status = self.get_status() 
            if not status['is_connected']:
                self._log.info('Focuser disconnected')

        except:
            self._log.critical('Disconnect failed')
            raise ConnectionException('Disconnect failed')
        return True
    
    def enable(self):
        status = self.get_status()
        try:
            if not status['is_enabled']:
                self.device.focuser_enable()
            else:
                pass
        except:
            self._log.critical('Focuser cannot be enabled')
            raise FocuserEnableFailedException()
        self._log.info('Focuer movement is enabled ')
        return True
    
    def disable(self):
        status = self.get_status()
        try:
            if status['is_enabled']:
                self.device.focuser_disable()
            else:
                pass
        except:
            self._log.critical('Focuser cannot be disabled')
            raise FocuserEnableFailedException()
        self._log.info('Focuer movement is disabled ')
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
        maxstep =  self.config['FOCUSER_MAXSTEP']
        minstep =  self.config['FOCUSER_MAXSTEP']
        if (position <= minstep) | (position > maxstep):
            self._log.critical('Set position is out of bound of this focuser (Min : %d Max : %d)'%(minstep, maxstep))
            raise FocusChangeFailedException('Set position is out of bound of this focuser (Min : %d Max : %d)'%(minstep, maxstep))
        else:
            status =  self.get_status()
            current_position = status['position']
            self._log.info('Moving focuser position... (Current : %s To : %s)'%(current_position, position))
            self.device.focuser_goto(target = position)
            time.sleep(self._checktime)
            status =  self.get_status()
            #while not np.abs(current_position - position) < 10:
            while status['is_moving']:
                status =  self.get_status()
                current_position = status['position']
                time.sleep(self._checktime)
                if abort_action.is_set():
                    self.abort()
                    self._log.warning('Focuser moving is aborted')
                    status =  self.get_status()
                    current_position = status['position']
                    raise AbortionException('Focuser moving is aborted (Current : %s)'%(current_position))
            status =  self.get_status()
            current_position = status['position']
            self._log.info('Focuser position is set (Current : %s)'%(current_position))
        return True
    
    def fans_on(self):
        self.device.fans_on()

    def fans_off(self):
        self.device.fans_off()

    def autofocus_start(self, 
                        abort_action : Event):
        status =  self.get_status()
        current_position = status['position']
        self._log.info('Start Autofocus (Center position : %s)'%(current_position))
        self.device.autofocus_start()
        time.sleep(self._checktime)
        status =  self.get_status()
        while status['is_autofocusing']:
            status =  self.get_status()
            time.sleep(self._checktime)
            if abort_action.is_set():
                self.autofocus_stop()
                self.abort()
                self._log.warning('Autofocus is aborted')
                status =  self.get_status()
                current_position = status['position']
                raise AbortionException('Autofocus is aborted (Current position : %s)'%(current_position))
        status =  self.get_status()
        while status['is_moving']:
            status =  self.get_status()
        status =  self.get_status()
        if status['is_autofocus_success']:
            self._log.info('Autofocus complete! (Best position : %s (%s))'%(status['autofocus_bestposition'], status['autofocus_tolerance']))
        else:
            self._log.warning('Autofocus failed')
            raise AutofocusFailedException('Autofocus failed')
        return True

    def autofocus_stop(self):
        self.device.autofocus_stop()
        
    def abort(self):
        """
        Abort the movement of the Focuser device
        """
        self.device.focuser_stop()   
        
# %% Test
if __name__ == '__main__':
    #Focus = Focuser('192.168.0.4:11111', 0)
    F = mainFocuser(unitnum = 2)
    F.connect()
    F.move(8000, Event())
# %%
