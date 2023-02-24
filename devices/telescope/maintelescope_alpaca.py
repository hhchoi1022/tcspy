#%%
# Other modules
import threading
import time
from typing import Optional
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.time import Time
#Alpaca modules
import alpaca
from alpaca.telescope import Telescope
from alpaca.exceptions import *
# TCSpy modules
from tcspy.utils import Timeout
from tcspy.utils import mainLogger
from tcspy.devices.observer import mainObserver
from tcspy.configuration import mainConfig
from tcspy.utils import to_SkyCoord
from tcspy.utils.target import mainTarget
#%%
log = mainLogger(__name__).log()
class mainTelescope_Alpaca(mainConfig):
    """
    Class for controlling an Alpaca telescope.

    Parameters
    ==========
    1. device : alpaca.telescope.Telescope
        The Alpaca telescope instance to control.
    2. Observer : mainObserver, optional
        The observer to use for calculations. If not provided, a new mainObserver instance will be created.

    Methods
    =======
    1. get_status() -> dict
        Returns the current status of the telescope.
    2. connect() -> None
        Connects to the telescope.
    3. disconnect() -> None
        Disconnects from the telescope.
    4. set_park(altitude : float = 40, azimuth : float = 180) -> None
        Sets the park position of the telescope.
    5. park() -> None
        Parks the telescope.
    6. unpark() -> None
        Unparks the telescope.
    7. slew_radec(coordinate : SkyCoord = None, ra : float = None, dec : float = None, target_name : str = '', tracking : bool = True) -> None
        Slews the telescope to the given RA and Dec or SkyCoord.
    8. slew_altaz(coordinate : SkyCoord = None, alt : float = None, az : float = None, tracking : bool = False) -> None
        Slew the telescope to the given Altitude and Azimuth coordinates in the horizontal coordinate system.
    9. tracking_on() -> None
        Turn on the telescope tracking.
    10. tracking_off() -> None
        Turn off the telescope tracking.
    11. abort() -> None
        Abort the movement of the scope
    """

    def __init__(self,
                 device : alpaca.telescope.Telescope,
                 observer : mainObserver,
                 **kwargs):
        
        # Load other modules
        super().__init__()
        self._min_altitude = float(self.config['TARGET_MINALT'])
        self._max_altitude = float(self.config['TARGET_MAXALT'])
        self._checktime = float(self.config['TELESCOPE_CHECKTIME'])
        self._lock_func = threading.Lock()
        self._abort = threading.Event()
        
        self.observer = observer
        if isinstance(device, alpaca.telescope.Telescope):
            self.device = device
            self.status = self.get_status()
        else:
            raise ValueError('Device type is not mathced to Alpaca Telescope')
        
    def get_status(self):

        status = dict()
        status['update_time'] = Time.now().iso
        status['jd'] = None
        status['ra'] = None
        status['dec'] = None
        status['alt'] = None
        status['az'] = None
        status['at_parked'] = None
        status['at_home'] = None
        status['is_connected'] = None
        status['is_tracking'] = None
        status['is_slewing'] = None
        status['is_stationary'] = None
        try:
            if self.device.Connected:
                try:
                    status['update_time'] = Time.now().iso
                except:
                    pass
                try:
                    status['jd'] = round(Time.now().jd,6)
                except:
                    pass
                try:
                    status['ra'] = round(self.device.RightAscension,5)
                except:
                    pass
                try:
                    status['dec'] = round(self.device.Declination,5)
                except:
                    pass
                try:
                    status['alt'] = round(self.device.Altitude,3)
                except:
                    pass
                try:
                    status['az'] = round(self.device.Azimuth,3)
                except:
                    pass
                try:
                    status['at_parked'] = self.device.AtPark
                except:
                    pass
                try:
                    status['at_home'] = self.device.AtHome
                except:
                    pass
                try:
                    status['is_connected'] = self.device.Connected
                except:
                    pass
                try:
                    status['is_tracking'] = self.device.Tracking
                except:
                    pass
                try:
                    status['is_slewing'] = self.device.Slewing
                except:
                    pass
                try:
                    status['is_stationary'] = not status['is_slewing']
                except:
                    pass
        except:
            pass
        return status
    
    @Timeout(5, 'Timeout')  
    def connect(self):
        """
        Connects to the telescope.
        """
        
        log.info('Connecting to the telescope...')
        try:
            if not self.device.Connected:
                self.device.Connected = True
            while not self.device.Connected:
                time.sleep(self._checktime)
            if  self.device.Connected:
                log.info('Telescope connected')
        except Exception as e:
            log.warning('Connection failed :', str(e))
        self.status = self.get_status()
            
    def disconnect(self):
        """
        Disconnects from the telescope.
        """
        
        self.device.Connected = False
        log.info('Disconnecting the telescope...')
        while self.device.Connected:
            time.sleep(self._checktime)
        if not self.device.Connected:
            log.info('Telescope disconnected')
        self.status = self.get_status()
    
    def set_park(self,
                 altitude : float = 40,
                 azimuth : float = 180):
        """
        Sets the park position of the telescope.

        Parameters
        ==========
        1. altitude : float, optional
            The altitude of the park position, in degrees. Default is 40.
        2. azimuth : float, optional
            The azimuth of the park position, in degrees. Default is 180.
        """
        
        coordinate = SkyCoord(azimuth, altitude, frame = 'altaz', unit ='deg')
        alt = coordinate.alt.deg
        az = coordinate.az.deg
        self.unpark()
        log.info('Setting park position of the telescope... Slew to the park position (Alt = %.1f Az = %.1f)'%(alt, az))
        self.slew_altaz(alt = alt, az = az, tracking = False)
        while self.device.Slewing:
            time.sleep(self._checktime)  
        self.device.SetPark()
        log.info('Park position is set (Alt = %.1f Az = %.1f)'%(alt, az))
        
    def park(self,
             altitude : float = 40,
             azimuth : float = 180):
        """
        Parks the telescope.
        """
        coordinate = SkyCoord(azimuth, altitude, frame = 'altaz', unit ='deg')
        alt = coordinate.alt.deg
        az = coordinate.az.deg
        
        if self.device.CanPark:
            #if not self.device.AtPark:
            log.info('Parking telescope...')
            self.slew_altaz(alt = alt, az = az, tracking = False)
            #self.device.Park() Read timeout?
            while self.device.Slewing:
                time.sleep(self._checktime)
                ################ timeout need to be implemented
            if not self.device.Slewing:
                log.info('Telescope parked')
        else:
            log.critical('Parking failed')
            raise SystemError('Parking failed')
    
    def unpark(self):
        """
        Unparks the telescope.
        """
        
        log.info('Unparking telescope...')
        if self.device.CanUnpark:
            if self.device.AtPark:
                self.device.Unpark()
                #while self.device.AtPark:
                #    time.sleep(self._checktime)
            if not self.device.AtPark:
                self.device.Tracking = False
            log.info('Telescope Unparked')
        else:
            log.critical('Unparking failed')
            raise SystemError('Unparking failed')

    def slew_radec(self,
                   coordinate : SkyCoord = None,
                   ra : float = None,
                   dec : float = None,
                   target_name : str = '',
                   tracking = True):
        """
        Slews the telescope to the given RA and Dec or SkyCoord.

        Parameters
        ==========
        1. coordinate : SkyCoord, optional
            The SkyCoord of the target. If not provided, RA and Dec must be provided. Default is None.
        2. ra : float, optional
            The right ascension of the target, in hours. If not provided, coordinate must be provided. Default is None.
        3. dec : float, optional
            The declination of the target, in degrees. If not provided, coordinate must be provided. Default is None.
        4. target_name : str, optional
            The name of the target. Default is an empty string.
        5. tracking : bool, optional
            Whether to start tracking after slewing to the target. Default is True.
        """
        
        if (ra != None) & (dec != None):
            coordinate = to_SkyCoord(ra, dec)
        ra = coordinate.ra.hour
        dec = coordinate.dec.deg
        target = mainTarget(self.observer, ra, dec, target_name)
        altaz = target.altaz()
        log.info('Slewing to the coordinate (RA = %.3f, Dec = %.3f, Alt = %.1f, Az = %.1f)' %(ra, dec, altaz.alt.deg, altaz.az.deg))

        # Check coordinates
        if altaz.alt.deg < self._min_altitude:
            log.critical('Destination altitude below limit (%.1fdeg)' %altaz.alt.deg)
            raise ValueError('Destination altitude below limit (%.1fdeg)' %altaz.alt.deg)
        
        # Slewing 
        if self.device.CanSlewAsync:

            if self.device.AtPark:
                self.unpark()
            if not self.device.Tracking:
                self.device.Tracking = True
            while not self.device.Tracking:
                time.sleep(self._checktime)
            self.device.SlewToCoordinatesAsync(ra, dec)
            while self.device.Slewing:
                time.sleep(self._checktime)
            status = self.get_status()
            log.info('Slewing finished. Current coordinate (RA = %.3f, Dec = %.3f, Alt = %.1f, Az = %.1f)' %(status['ra'], status['dec'], status['alt'], status['az']))
            if not tracking:
                self.device.Tracking = False
        else:
            log.critical('Slewing failed')
            
    def slew_altaz(self,
                   coordinate : SkyCoord = None,
                   alt : float = None,
                   az : float = None,
                   tracking = False):
        """
        Slew the telescope to the given Altitude and Azimuth coordinates in the horizontal coordinate system.

        Parameters
        ==========
        1. coordinate : SkyCoord object, optional
            SkyCoord object containing the Altitude and Azimuth coordinates.
        2. alt : float, optional
            Altitude coordinate in degrees.
        3. az : float, optional
            Azimuth coordinate in degrees.
        4. tracking : bool, optional
            If True, activate the telescope tracking feature after slewing. Default is False.
        """
        
        if coordinate == None:
            coordinate = SkyCoord(az, alt, frame = 'altaz', unit ='deg')
        alt = coordinate.alt.deg
        az = coordinate.az.deg
        log.info('Slewing to the coordinate (Alt = %.1f, Az = %.1f)' %(alt, az))

        # Check coordinates
        if alt < self._min_altitude:
            log.critical('Destination altitude below limit (%.1fdeg)' %alt)
            raise ValueError('Destination altitude below limit (%.1fdeg)' %alt)
        
        # Slewing 
        if self.device.CanSlewAsync:
            if self.device.AtPark:
                self.unpark()
            if self.device.Tracking:
                self.device.Tracking = False
            while self.device.Tracking:
                time.sleep(self._checktime)
            self.device.SlewToAltAzAsync(az, alt)
            while self.device.Slewing:
                time.sleep(self._checktime)
            status = self.get_status()
            log.info('Slewing finished. Current coordinate (Alt = %.1f, Az = %.1f)' %(status['alt'], status['az']))
            if tracking:
                self.device.Tracking = True
        else:
            log.critical('Slewing failed')

    def tracking_on(self):
        """
        Turn on the telescope tracking.
        """
        
        if self.device.CanSetTracking:
            if not self.device.Tracking:
                self.device.Tracking = True
                while not self.device.Tracking:
                    time.sleep(self._checktime)
            if  self.device.Tracking:
                log.info('Tracking activated')
        else:
            log.critical('Tracking failed')
            raise SystemError('Tracking failed')
    
    def tracking_off(self):
        """
        Turn off the telescope tracking.
        """
        
        if self.device.CanSetTracking:
            if self.device.Tracking:
                self.device.Tracking = False
                while self.device.Tracking:
                    time.sleep(self._checktime)
            if not self.device.Tracking:
                log.info('Tracking deactivated')
        else:
            log.critical('Untracking failed')
            raise SystemError('Untracking failed')
    
    def abort(self):
        """
        Abort the movement of the mount
        """
        
        self.device.AbortSlew()
        log.warning('Telescope aborted')
        
#%% Test  
            
if __name__ == '__main__':

    T = Telescope('localhost:32323',0)
    config = mainConfig().config
    Tel = mainTelescope_Alpaca(device= T, observer = mainObserver(**config))
    Tel.connect()
    
#%%

    ra = '15:35:28'
    dec = '-50:39:32'
    
    coordinate_radec = to_SkyCoord(ra, dec)
    Tel.set_park(altitude = 30, azimuth = 180)
    
    Tel.slew_radec(coordinate_radec, tracking = True)

    alt = 50.23
    az = 170.23
    
    Tel.park()
    Tel.unpark()
    coordinate_altaz = SkyCoord(az, alt, frame = 'altaz', unit = 'deg')
    Tel.slew_radec(coordinate_radec, tracking = True)
    Tel.slew_altaz(alt = alt, az = az)
    Tel.set_park()
    Tel.tracking_on()
    Tel.tracking_off()
    Tel.park()
    Tel.disconnect()
# %%
