#%%
from astropy.io import ascii
from astropy.time import Time
import time
import json
from alpaca.filterwheel import FilterWheel

from tcspy.utils.logger import mainLogger
from tcspy.utils import Timeout
from tcspy.configuration import mainConfig
from tcspy.utils.exception import *
from tcspy.utils import FocusModel

# %%
class mainFilterwheel(mainConfig):
    """
    This class provides an interface to interact with a filter wheel device.

    Parameters
    ==========
    1. device : alpaca.filterwheel.FilterWheel
        The filter wheel device to interact with.

    Methods
    =======
    1. get_status() -> dict
        Returns a dictionary containing the current status of the filter wheel.
    2. connect()
        Connects to the filter wheel device.
    3. disconnect()
        Disconnects from the filter wheel device.
    4. move(filter_ : str or int)
        Moves the filter wheel to the specified filter position or filter name.
    5. abort()
        Dummy abort action. No supported action exists
    """
    
    def __init__(self,
                 unitnum : int,
                 **kwargs):
        super().__init__(unitnum = unitnum)
        self._log = mainLogger(unitnum = unitnum, logger_name = __name__+str(unitnum)).log()
        self._checktime = float(self.config['FTWHEEL_CHECKTIME'])
        self.device = FilterWheel(f"{self.config['FTWHEEL_HOSTIP']}:{self.config['FTWHEEL_PORTNUM']}",self.config['FTWHEEL_DEVICENUM'])        
        self.filtnames = None
        self.offsets = None
        self.filtnames = self._get_all_filt_names()
        self.offsets = self._get_all_filt_offset()
        self.status = self.get_status()
        
    def get_status(self) -> dict:
        """
        Returns a dictionary containing the current status of the filter wheel.

        Return
        ======
        1. status : dict
            A dictionary containing the current status of the filter wheel.
        """

        status = dict()
        status['update_time'] = Time.now().isot
        status['jd'] = round(Time.now().jd,6)
        status['is_connected'] = False
        status['name'] = None
        status['filter'] = None
        status['offset'] = None

        if self.device.Connected:
            try:              
                filtinfo = self._get_current_filtinfo()
            except:
                pass
            try:
                status['update_time'] = Time.now().isot
            except:
                pass
            try:
                status['jd'] = round(Time.now().jd,6)
            except:
                pass
            try:
                status['name'] = self.device.Name
            except:
                pass
            try:
                status['filter'] = filtinfo['name']
            except:
                pass
            try:
                status['offset'] = filtinfo['offset']
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
        Connects to the filter wheel device.
        """
        
        self._log.info('Connecting to the filterwheel...')
        try:
            if not self.device.Connected:
                self.device.Connected = True
            time.sleep(self._checktime)
            while not self.device.Connected:
                time.sleep(self._checktime)
            if  self.device.Connected:
                self._log.info('Filterwheel connected')
        except:
            self._log.warning('Connection failed')
            raise ConnectionException('Connection failed')
        return True
    
    @Timeout(5, 'Timeout')
    def disconnect(self):
        """
        Disconnects from the filter wheel device.
        """
        
        self._log.info('Disconnecting filterwheel...')
        try:
            if self.device.Connected:
                self.device.Connected = False
                time.sleep(self._checktime)
            while self.device.Connected:
                time.sleep(self._checktime)
            if not self.device.Connected:
                self._log.info('Filterwheel is disconnected')
        except:
            self._log.warning('Disconnect failed')
            raise ConnectionException('Disconnect failed')
        return True
            
    def move(self,
             filter_ : str or int) -> bool:
        """
        Moves the filter wheel to the specified filter position or filter name.

        Parameters
        ==========
        1. filter_ : str or int
            The position or name of the filter to move to.
        """
        # Check whether the input filter is implemented
        current_filter = self._get_current_filtinfo()['name']
        if isinstance(filter_, str):
            if not filter_ in self.filtnames:
                self._log.critical(f'Filter {filter_} is not implemented [{self.filtnames}]')
                raise FilterChangeFailedException(f'Filter {filter_} is not implemented [{self.filtnames}]')
            else:
                self._log.info('Changing filter... (Current : %s To : %s)'%(current_filter, filter_))
                filter_ = self._filtname_to_position(filter_)
        else:
            if filter_ > len(self.filtnames):
                self._log.critical(f'Position "{filter_}" is not implemented')
                raise FilterChangeFailedException(f'Position "{filter_}" is not implemented')
            else:
                self._log.info('Changing filter... (Current : %s To : %s)'%(current_filter, self._position_to_filtname(filter_)))
        
        # Change filter
        try:
            self.device.Position = filter_
        except:
            pass
        time.sleep(self._checktime)
        while not self.device.Position == filter_:
            time.sleep(self._checktime)
            
        # Return result
        self._log.info('Filter changed (Current : %s)'%(self._get_current_filtinfo()['name']))
        return True

    def get_offset_from_currentfilt(self,
                                    filter_ : str):
        current_filter = self._get_current_filtinfo()['name']
        offset = self.calc_offset(current_filt= current_filter, changed_filt = filter_)
        return offset 
        
    def abort(self):
        return
    
    # Information giding
    def _get_all_filt_names(self) -> list:
        """
        Returns a list of all filter names configured for the filter wheel.

        Return
        ======
        1. filtnames : list
            A list of all filter names configured for the filter wheel.
        """
        if self.device.Names is None:
            raise FilterRegisterException("No filter information is registered")
        filtnames = self.device.Names
        return filtnames
        
    def _get_all_filt_offset(self) -> list:
        """
        Returns a list of all filter offsets configured for the filter wheel.

        Return
        ======
        1. filtnames : list
            A list of all filter offsets configured for the filter wheel.
        """
        '''
        if self.device.Names is None:
            raise FilterRegisterException("No filter information is registered")
        filtoffsets = self.device.FocusOffsets
        filtnames = self.device.Names
        info_offset = dict(zip(filtnames, filtoffsets))'''
        with open(self.config['FTWHEEL_OFFSETFILE'], 'r') as f:
            info_offset = json.load(f)
            del info_offset['updated_date']
        filters_in_config = set(info_offset.keys())
        filters_in_device = set(self._get_all_filt_names())
        if filters_in_device.issubset(filters_in_config):
            pass
        else:
            raise FilterRegisterException(f'Registered filters are not matched with configured filters \n Configured = [{filters_in_config}] \n Registered = [{filters_in_device}]')
        return info_offset
    
    def _position_to_filtname(self,
                              position : int) -> str:
        """
        Converts a filter position to its corresponding filter name.

        Parameters
        ==========
        1. position : int
            The position of the filter to get the name of.

        Return
        ======
        1. filtname : str
            The name of the filter at the specified position.
        """
        
        try:
            return self.filtnames[position]  
        except:
            self._log.warning('Position "%s" is out of range of the filterwheel'%position)
            raise FilterRegisterException('Position "%s" is out of range of the filterwheel'%position)
        
    def _filtname_to_position(self,
                              filtname : str) -> int:
        """
        Converts a filter name to its corresponding filter position.

        Parameters
        ==========
        1. filtname : str
            The name of the filter to get the position of.

        Return
        ======
        1. position : int
            The position of the filter with the specified name.
        """
        
        try:
            return self.filtnames.index(filtname)
        except:
            self._log.warning('%s is not implemented in the filterwheel'%filtname)
            raise FilterRegisterException('%s is not implemented in the filterwheel'%filtname)
    
    def _is_connected(self) -> bool:
        """
        Returns True if the filter wheel device is connected, False otherwise.

        Return
        ======
        1. connected : bool
            True if the filter wheel device is connected, False otherwise.
        """
        
        return self.device.Connected
    
    def _get_current_filtinfo(self) -> str:
        """
        Returns a dictionary containing information about the current filter.

        Return
        ======
        1. filtinfo : dict
            A dictionary containing information about the current filter, including its position, name, and offset.
        """
        
        position = self.device.Position
        filtname = self._position_to_filtname(position = position)
        return dict( position = position, name = self.filtnames[position], offset = self.offsets[filtname]['offset'])
    
    def calc_offset(self,
                    current_filt : str,
                    changed_filt : str) -> int:
        try:
            offset_current = self.offsets[current_filt]['offset']
            offset_changed = self.offsets[changed_filt]['offset']
            return offset_changed - offset_current
        except:
            raise FilterRegisterException(f'Filter: {current_filt}, {changed_filt} is not registered')

        
        
# %% Test
if __name__ == '__main__':
    F = mainFilterwheel(unitnum= 1)
    #F.connect()
    print(F.device.Names)
    #F.move('NoFilter', return_focus_offset= True)
    #F.disconnect()

# %%
