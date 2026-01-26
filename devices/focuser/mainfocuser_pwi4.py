#%%
from astropy.io import ascii
import time
import json, os
from astropy.time import Time
import numpy as np
from multiprocessing import Event
from multiprocessing import Lock

from tcspy.devices import PWI4
from tcspy.utils.logger import mainLogger
from tcspy.utils import Timeout
from tcspy.configuration import mainConfig
from tcspy.utils.exception import *

# %%
class mainFocuser_pwi4(mainConfig):
    """
    A class for controlling a Focuser device.

    Parameters
    ----------
    unitnum : int
        The unit number.

    Attributes
    ----------
    device : PWI4
        The Focuser device to control.
    status : dict
        A dictionary containing the current status of the Focuser device.

    Methods
    -------
    get_status() -> dict
        Get the status of the Focuser device.
    connect() -> bool
        Connect to the telescope.
    disconnect() -> bool
        Disconnect from the telescope.
    enable() -> bool
        Enable focuser movement.
    disable() -> bool
        Disable focuser movement.
    move(position: int, abort_action: Event) -> bool
        Move the Focuser device to the specified position.
    fans_on() -> bool
        Turn on the fans.
    fans_off() -> bool
        Turn off the fans.
    autofocus_start(abort_action: Event) -> bool
        Start autofocus.
    autofocus_stop() -> None
        Stop autofocus.
    abort() -> None
        Abort the movement of the Focuser device.
    """
    
    def __init__(self,
                 unitnum : int,
                 **kwargs):
        
        super().__init__(unitnum = unitnum)
        self.device = PWI4(self.config['FOCUSER_HOSTIP'], self.config['FOCUSER_PORTNUM'])
        self.is_idle = Event()
        self.is_idle.set()
        self.device_lock = Lock()
        self._log = mainLogger(unitnum = unitnum, logger_name = __name__+str(unitnum)).log()
        self._id = None
        self._id_update_time = None
        self.status = self.get_status()
        
 
    @property
    def id(self):
        ### SPECIFIC for 7DT
        def load_id(self):
            dict_file = self.config['MULTITELESCOPES_FILE']
            with open(dict_file, 'r') as f:
                import json
                data_dict = json.load(f)
            return data_dict[self.tel_name]['Focuser']['name']
        if self._id is None:
            try:
                self._id = load_id(self)
            except:
                pass
        return self._id
    
    @property
    def id_update_time(self):
        ### SPECIFIC for 7DT
        def load_id(self):
            dict_file = self.config['MULTITELESCOPES_FILE']
            with open(dict_file, 'r') as f:
                import json
                data_dict = json.load(f)
            return data_dict[self.tel_name]['Focuser']['timestamp']
        if self._id_update_time is None:
            try:
                self._id_update_time = load_id(self)
            except:
                pass
        return self._id_update_time
    
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
        status['position'] = None
        status['is_connected'] = False
        status['is_enabled'] = None
        status['is_moving'] = None
        status['is_autofocusing'] = None
        status['is_autofocus_success'] = None
        status['autofocus_bestposition'] = None
        status['autofocus_tolerance'] = None
        status['autofocus_history'] = self._get_autofocus_history()
        status['focuser_id'] = self.id
        status['focuser_id_update_time'] = self.id_update_time
        
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
        """
        Property to get the PWI status.

        Returns
        -------
        PWI status
            The PWI status of the device.
        """
        return self.device.status()
    
    def _get_autofocus_history(self):
        af_path = os.path.join(self.config['AUTOFOCUS_FOCUSHISTORY_PATH'], self.tel_name, 'focus_history.json')
        if os.path.exists(af_path):
            with open(af_path, 'r') as f:
                data = json.load(f)
            return data
        else:
            return None
    
    @Timeout(5, 'Timeout')
    def connect(self):
        """
        Connect to the focuser.
        """
        self._log.info('Connecting to the focuser...')
        status = self.get_status()
        try:
            if not status['is_connected']:
                self.device.focuser_connect()
            time.sleep(float(self.config['FOCUSER_CHECKTIME']))
            while not status['is_connected']:
                time.sleep(float(self.config['FOCUSER_CHECKTIME']))
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
            time.sleep(float(self.config['FOCUSER_CHECKTIME']))
            while status['is_connected']:
                time.sleep(float(self.config['FOCUSER_CHECKTIME']))
                status = self.get_status() 
            if not status['is_connected']:
                self._log.info('Focuser disconnected')
        except:
            self._log.critical('Disconnect failed')
            raise ConnectionException('Disconnect failed')
        return True
    
    def enable(self):
        """
        Enable focuser movement.
        """
        status = self.get_status()
        try:
            if not status['is_enabled']:
                self.device.focuser_enable()
            else:
                pass
            self._log.info('Focuer movement is enabled ')
        except:
            self._log.critical('Focuser cannot be enabled')
            raise FocuserEnableFailedException()
        return True
    
    def disable(self):
        """
        Disable focuser movement.
        """
        status = self.get_status()
        try:
            if status['is_enabled']:
                self.device.focuser_disable()
            else:
                pass
            self._log.info('Focuer movement is disabled ')
        except:
            self._log.critical('Focuser cannot be disabled')
            raise FocuserEnableFailedException()
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
        abort_action : Event
            Event object for aborting the movement.
        """
        self.is_idle.clear()
        self.device_lock.acquire()
        exception_raised = None
        
        try:
            maxstep =  self.config['FOCUSER_MAXSTEP']
            minstep =  self.config['FOCUSER_MINSTEP']
            if (position <= minstep) | (position > maxstep):
                self._log.critical('Set position is out of bound of this focuser (Min : %d Max : %d)'%(minstep, maxstep))
                raise FocusChangeFailedException('Set position is out of bound of this focuser (Min : %d Max : %d)'%(minstep, maxstep))
            else:
                status =  self.get_status()
                current_position = status['position']
                self._log.info('Moving focuser position... (Current : %s To : %s)'%(current_position, position))
                self.device.focuser_goto(target = position)
                time.sleep(float(self.config['FOCUSER_CHECKTIME']))
                status =  self.get_status()
                while status['is_moving']:
                    status =  self.get_status()
                    current_position = status['position']
                    time.sleep(float(self.config['FOCUSER_CHECKTIME']))
                    if abort_action.is_set():
                        self.device.focuser_stop()   
                        time.sleep(float(self.config['FOCUSER_CHECKTIME']))
                        raise AbortionException('Focuser movement is aborted')
                time.sleep(3 * float (self.config['FOCUSER_CHECKTIME']))
                status =  self.get_status()
                current_position = status['position']
                self._log.info('Focuser position is set (Current : %s)'%(current_position))
            return True
        
        except Exception as e:
            exception_raised = e
        
        finally:
            self.device_lock.release()
            self.is_idle.set()
            if exception_raised:
                raise exception_raised
    
    def fans_on(self):
        """
        Turn on the fans.
        
        Raises
        ------
        FocusFansFailedException
            If fans cannot be turned on.
        """
        try:
            self.device.fans_on()
            self._log.info('Fans are turned on')
        except:
            self._log.critical('Fans cannot be turned on')
            raise FocusFansFailedException('Fans cannot be turned on')
        return True

    def fans_off(self):
        """
        Turn off the fans.
        
        Raises
        ------
        FocusFansFailedException
            If fans cannot be turned off.
        """
        try:
            self.device.fans_off()
            self._log.info('Fans are turned off')
        except:
            self._log.critical('Fans cannot be turned off')
            raise FocusFansFailedException('Fans cannot be turned off')
        return True

    def autofocus_start(self, 
                        abort_action : Event):
        """
        Start autofocus.

        Parameters
        ----------
        abort_action : Event
            Event object for aborting the autofocus.
        
        Raises
        ------
        AbortionException
            If autofocus is aborted.
        AutofocusFailedException
            If autofocus fails.

        """
        self.is_idle.clear()
        self.device_lock.acquire()
        exception_raised = None
        
        try:
            status =  self.get_status()
            current_position = status['position']
            self._log.info('Start autofocus (Central position : %s)'%(current_position))
            self.device.autofocus_start()
            time.sleep(float(self.config['FOCUSER_CHECKTIME']))
            status =  self.get_status()
            while status['is_autofocusing']:
                status =  self.get_status()
                time.sleep(float(self.config['FOCUSER_CHECKTIME']))
                if abort_action.is_set():
                    self.device.autofocus_stop()
                    while status['is_moving']:
                        status =  self.get_status()
                    self._log.warning('Autofocus is aborted. Move back to the previous position')
                    self.device_lock.release()
                    self.move(position = current_position, abort_action= Event())
                    self.device_lock.acquire() 
                    raise AbortionException('Autofocus is aborted. Move back to the previous position')
            status =  self.get_status()
            while status['is_moving']:
                status =  self.get_status()
            time.sleep(3 * float(self.config['FOCUSER_CHECKTIME']))
            status =  self.get_status()
            if (status['is_autofocus_success']) & (status['autofocus_tolerance'] < self.config['AUTOFOCUS_TOLERANCE']):
                self._log.info('Autofocus complete! (Best position : %s (%s))'%(status['autofocus_bestposition'], status['autofocus_tolerance']))
                return status['is_autofocus_success'], status['autofocus_bestposition'], status['autofocus_tolerance']
            else:
                self.device_lock.release()
                self.move(position = current_position, abort_action= Event())
                self.device_lock.acquire()
                self._log.warning('Autofocus failed. Move back to the previous position')
                raise AutofocusFailedException('Autofocus failed. Move back to the previous position')
        except Exception as e:
            exception_raised = e
            print(exception_raised)
        
        finally:
            self.device_lock.release()
            self.is_idle.set()
            if exception_raised:
                raise exception_raised
            
    def wait_idle(self):
        self.is_idle.wait()
