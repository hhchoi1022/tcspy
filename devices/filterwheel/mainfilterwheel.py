#%%
# Other modules
from astropy.io import ascii
from astropy.time import Time
import time
import json
# Alpaca modules
from alpaca.filterwheel import FilterWheel
import alpaca
# TCSpy modules
from tcspy.utils import mainLogger
from tcspy.utils import Timeout
from tcspy.configuration import mainConfig

# %%
log = mainLogger(__name__).log()
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
                 device : alpaca.filterwheel.FilterWheel):
        super().__init__()
        self._checktime = float(self.config['FTWHEEL_CHECKTIME'])
        self._filternames = self._get_all_filt_names()
        self._filteroffset = self._get_all_filt_offset()
        
        if isinstance(device, alpaca.filterwheel.FilterWheel):
            self.device = device
            self.status = self.get_status()
        else:
            log.warning('Device type is not mathced to Alpaca Filterwheel')
            raise ValueError('Device type is not mathced to Alpaca Filterwheel')
        
    def get_status(self) -> dict:
        """
        Returns a dictionary containing the current status of the filter wheel.

        Return
        ======
        1. status : dict
            A dictionary containing the current status of the filter wheel.
        """

        status = dict()
        status['update_time'] = Time.now().iso
        status['jd'] = None
        status['name'] = None
        status['filter'] = None
        status['offset'] = None
        status['is_connected'] = None
        try:
            if self.device.Connected:     
                try:              
                    filtinfo = self._get_current_filtinfo()
                except:
                    pass
                try:
                    status['update_time'] = Time.now().iso
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
        except:
            pass
        return status

    @Timeout(5, 'Timeout')
    def connect(self):
        """
        Connects to the filter wheel device.
        """
        
        log.info('Connecting to the Filterwheel...')
        try:
            if not self.device.Connected:
                self.device.Connected = True
            while not self.device.Connected:
                time.sleep(self._checktime)
            if  self.device.Connected:
                log.info('Filterwheel connected')
        except:
            log.warning('Connection failed')
        self.status = self.get_status()
    
    def disconnect(self):
        """
        Disconnects from the filter wheel device.
        """
        
        self.device.Connected = False
        log.info('Disconnecting the Filterwheel...')
        while self.device.Connected:
            time.sleep(self._checktime)
        if not self.device.Connected:
            log.info('Filterwheel disconnected')
        self.status = self.get_status()
            
    def move(self,
             filter_ : str or int):
        """
        Moves the filter wheel to the specified filter position or filter name.

        Parameters
        ==========
        1. filter_ : str or int
            The position or name of the filter to move to.
        """
        
        if isinstance(filter_, str):
            log.info('Changing filter... (Current : %s To : %s)'%(self._get_current_filtinfo()['name'], filter_))
            filter_ = self._filtname_to_position(filter_)
        else:
            log.info('Changing filter... (Current : %s To : %s)'%(self._get_current_filtinfo()['name'], self._position_to_filtname(filter_)))
        self.device.Position = filter_
        while not self.device.Position == filter_:
            time.sleep(self._checktime)
        log.info('Filter changed (Current : %s)'%(self._get_current_filtinfo()['name']))
    
    def abort(self):
        pass
    
    # Information giding
    def _get_all_filt_names(self) -> list:
        """
        Returns a list of all filter names configured for the filter wheel.

        Return
        ======
        1. filtnames : list
            A list of all filter names configured for the filter wheel.
        """
        
        with open(self.config['FTWHEEL_OFFSETFILE'], 'r') as f:
            filtnames = list(json.load(f).keys())
        return filtnames
        
    def _get_all_filt_offset(self) -> list:
        """
        Returns a list of all filter offsets configured for the filter wheel.

        Return
        ======
        1. filtnames : list
            A list of all filter offsets configured for the filter wheel.
        """
        
        with open(self.config['FTWHEEL_OFFSETFILE'], 'r') as f:
            filtnames = list(json.load(f).values())
        return filtnames
    
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
            return self._filternames[position]  
        except:
            log.warning('%s is out of range of the filterwheel'%position)
        
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
            return self._filternames.index(filtname)
        except:
            log.warning('%s is not implemented in the filterwheel'%filtname)
    
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
        return dict( position = position, name = self._filternames[position], offset = self._filteroffset[position])
    

        
        
# %% Test
if __name__ == '__main__':
    Filt = FilterWheel('127.0.0.1:32323', 0)
    F = mainFilterwheel(Filt)
    #%%
    F.connect()
    F._name()
    F._get_all_filt_names()
    F._get_all_filt_offset()
    F._get_current_filtinfo()
    F._position_to_filtname(5)
    F._filtname_to_position('w400')
    F.move('w425')
    F._get_current_filtinfo()
# %%

# %%
