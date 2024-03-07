#%%
import time
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.time import Time
from threading import Event

from alpaca.telescope import Telescope
from alpaca.exceptions import *

from tcspy.utils import Timeout
from tcspy.utils.logger import mainLogger
from tcspy.devices.observer import mainObserver
from tcspy.configuration import mainConfig
from tcspy.utils import to_SkyCoord
from tcspy.utils.target import SingleTarget
from tcspy.utils.exception import *

#%%
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
                 unitnum : int,
                 **kwargs):
        super().__init__(unitnum = unitnum)
        self._log = mainLogger(unitnum = unitnum, logger_name = __name__+str(unitnum)).log()
        self._min_altitude = float(self.config['TARGET_MINALT'])
        self._max_altitude = float(self.config['TARGET_MAXALT'])
        self._settle_time = float(self.config['TELESCOPE_SETTLETIME'])
        self._checktime = float(self.config['TELESCOPE_CHECKTIME'])
        self.observer = mainObserver(unitnum = unitnum)
        self.device = Telescope(f"{self.config['TELESCOPE_HOSTIP']}:{self.config['TELESCOPE_PORTNUM']}",self.config['TELESCOPE_DEVICENUM'])
        self.status = self.get_status()
        
    def get_status(self):

        status = dict()
        status['update_time'] = Time.now().isot
        status['jd'] = "{:.6f}".format(Time.now().jd)
        status['ra'] = None
        status['dec'] = None
        status['alt'] = None
        status['az'] = None
        status['at_parked'] = None
        status['is_connected'] = False
        status['is_tracking'] = None
        status['is_slewing'] = None
        status['is_stationary'] = None

        if self.device.Connected:
            try:
                status['update_time'] = Time.now().isot
            except:
                pass
            try:
                status['jd'] = "{:.6f}".format(Time.now().jd)
            except:
                pass
            try:
                coordinates = SkyCoord(self.device.RightAscension, self.device.Declination, unit = (u.hourangle, u.deg) )
                status['ra'] =  float("{:.4f}".format(coordinates.ra.deg))
                status['dec'] =  float("{:.4f}".format(coordinates.dec.deg))
            except:
                pass
            try:
                status['ra_hour'] =  float("{:.4f}".format(self.device.RightAscension))
            except:
                pass
            try:
                status['dec_deg'] =  float("{:.4f}".format(self.device.Declination))
            except:
                pass
            try:
                status['alt'] =  float("{:.3f}".format(self.device.Altitude))
            except:
                pass
            try:
                status['az'] =  float("{:.3f}".format(self.device.Azimuth))
            except:
                pass
            try:
                status['at_parked'] = self.device.AtPark
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

        return status
    
    @Timeout(5, 'Timeout')  
    def connect(self):
        """
        Connects to the telescope.
        """
        
        self._log.info('Connecting to the telescope...')
        try:
            if not self.device.Connected:
                self.device.Connected = True
            time.sleep(self._checktime)
            while not self.device.Connected:
                time.sleep(self._checktime)
            if  self.device.Connected:
                self._log.info('Telescope connected')
        except:
            self._log.warning('Connection failed')
            raise ConnectionException('Connection failed')
        return True
    
    @Timeout(5, 'Timeout') 
    def disconnect(self):
        """
        Disconnects from the telescope.
        """
        
        self._log.info('Disconnecting telescope...')
        try:
            if self.device.Connected:
                self.device.Connected = False
                time.sleep(self._checktime)
            while self.device.Connected:
                time.sleep(self._checktime)
            if not self.device.Connected:
                self._log.info('Telescope is disconnected')
        except:
            self._log.warning('Disconnect failed')
            raise ConnectionException('Disconnect failed')
        return True
        
    def park(self,
             abort_action : Event):
        """
        Parks the telescope.
        """
        coordinate = SkyCoord(self.config['TELESCOPE_PARKAZ'],self.config['TELESCOPE_PARKALT'], frame = 'altaz', unit ='deg')
        alt = coordinate.alt.deg
        az = coordinate.az.deg
        
        #if self.device.CanPark:
            #if not self.device.AtPark:
        self._log.info('Parking telescope...')
        if self.device.CanSlewAsync:

            if self.device.Tracking:
                self.device.Tracking = False
            while self.device.Tracking:
                time.sleep(self._checktime)
            if self.device.AtPark:
                pass
            else:
                self.device.SlewToAltAzAsync(az, alt)
            time.sleep(self._checktime)
            while self.device.Slewing:
                time.sleep(self._checktime)
                if abort_action.is_set():
                    self.abort()
                    self._log.warning('Telescope parking is aborted')
                    raise AbortionException('Telescope parking is aborted')
            time.sleep(self._checktime)
            self._log.info('Telescope parked')
        else:
            self._log.critical('Parking failed')
            raise ParkingFailedException('Parking failed')
        return True
    
    def unpark(self):
        """
        Unparks the telescope.
        """
        
        self._log.info('Unparking telescope...')
        if self.device.CanUnpark:
            if self.device.AtPark:
                self.device.Unpark()
            self.device.Tracking = False
            self._log.info('Telescope Unparked')
            return True
        else:
            self._log.critical('Unparking failed')
            raise ParkingFailedException('Unparking failed')
        

    def slew_radec(self,
                   ra : float,
                   dec : float,
                   abort_action : Event,
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
        
        target = SingleTarget(unitnum = self.unitnum, observer = self.observer, target_ra = float(ra), target_dec = float(dec))
        altaz = target.altaz()
        self._log.info('Slewing to the coordinate (RA = %.3f, Dec = %.3f, Alt = %.1f, Az = %.1f)' %(ra, dec, altaz.alt.deg, altaz.az.deg))

        # Check coordinates
        if altaz.alt.deg < self._min_altitude:
            self._log.critical('Destination altitude below limit (%.1fdeg)' %altaz.alt.deg)
            raise SlewingFailedException('Destination altitude below limit (%.1fdeg)' %altaz.alt.deg)
        
        # Slewing 
        else:
            if self.device.CanSlewAsync:
                if self.device.AtPark:
                    try:
                        self.unpark()
                    except ParkingFailedException:
                        raise SlewingFailedException('Telescope slewing is failed : Unpark failed')
                #self.device.Tracking = False 
                #while self.device.Tracking:
                #    time.sleep(self._checktime)
                self.device.SlewToCoordinatesAsync(target.ra_hour, target.dec_deg)
                time.sleep(self._checktime)
                while self.device.Slewing:
                    time.sleep(self._checktime)
                    if abort_action.is_set():
                        self.abort()
                        self._log.warning('Telescope slewing is aborted')
                        raise AbortionException('Telescope slewing is aborted')
                self._log.info(f'Telescope settling for {self.config["TELESCOPE_SETTLETIME"]}s...' )
                time.sleep(self._settle_time)
                self.status = self.get_status()
                self._log.info('Slewing finished. Current coordinate (RA = %.3f, Dec = %.3f, Alt = %.1f, Az = %.1f)' %(self.status['ra'], self.status['dec'], self.status['alt'], self.status['az']))
                if not tracking:
                    try:
                        self.tracking_off()
                    except TrackingFailedException:
                        raise SlewingFailedException('Telescope slewing is failed : Tracking failed')
                else:
                    try:
                        self.tracking_on()
                    except TrackingFailedException:
                        raise SlewingFailedException('Telescope slewing is failed : Tracking failed')                    
                return True
            else:
                self._log.critical('Slewing failed')
                raise SlewingFailedException('Slewing failed')
            
    def slew_altaz(self,
                   alt : float,
                   az : float,
                   abort_action : Event,
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
        
        self._log.info('Slewing to the coordinate (Alt = %.1f, Az = %.1f)' %(alt, az))

        # Check coordinates
        if alt < self._min_altitude:
            self._log.critical('Destination altitude below limit (%.1fdeg)' %alt)
            raise SlewingFailedException('Destination altitude below limit (%.1fdeg)' %alt)
        
        # Slewing 
        else:
            if self.device.CanSlewAsync:
                if self.device.AtPark:
                    try:
                        self.unpark()
                    except ParkingFailedException:
                        raise SlewingFailedException('Unpark failed')
                self.device.SlewToAltAzAsync(az, alt)
                time.sleep(self._checktime)
                while self.device.Slewing:
                    time.sleep(self._checktime)
                    if abort_action.is_set():
                        self.abort()
                        self._log.warning('Telescope slewing is aborted')
                        raise AbortionException('Telescope slewing is aborted')
                self._log.info(f'Telescope settling for {self.config["TELESCOPE_SETTLETIME"]}s...' )
                time.sleep(self._settle_time)
                self.status = self.get_status()
                self._log.info('Slewing finished. Current coordinate (Alt = %.1f, Az = %.1f)' %(self.status['alt'], self.status['az']))
                if tracking:
                    try:
                        self.tracking_on()
                    except TrackingFailedException:
                        raise SlewingFailedException('Tracking failed')
                return True
            else:
                self._log.critical('Slewing failed')
                raise SlewingFailedException('Slewing failed')

    def tracking_on(self):
        """
        Turn on the telescope tracking.
        """
        
        if self.device.CanSetTracking:
            if not self.device.Tracking:
                time.sleep(self._checktime)
                self.device.Tracking = True
                while not self.device.Tracking:
                    time.sleep(self._checktime)
            if  self.device.Tracking:
                self._log.info('Tracking activated')
            return True
        else:
            self._log.critical('Tracking failed')
            raise TrackingFailedException('Tracking failed')
    
    def tracking_off(self):
        """
        Turn off the telescope tracking.
        """
        
        if self.device.CanSetTracking:
            if self.device.Tracking:
                self.device.Tracking = False
                time.sleep(self._checktime)
                while self.device.Tracking:
                    time.sleep(self._checktime)
            if not self.device.Tracking:
                self._log.info('Tracking deactivated')
            return True
        else:
            self._log.critical('Untracking failed')
            raise TrackingFailedException('Untracking failed')
    
    def abort(self):
        """
        Abort the movement of the mount
        """
        self.device.AbortSlew()
        
#%% Test  
            
if __name__ == '__main__':
    Tel = mainTelescope_Alpaca(unitnum = 1)
    Tel.connect()
    ra = '15:35:28'
    dec = '40:39:32'
    coordinate_radec = to_SkyCoord(ra, dec)

    #Tel.slew_radec(coordinate_radec, tracking = True)
    alt = 20
    az = 230

    Tel.park()
    Tel.unpark()
    coordinate_altaz = SkyCoord(az, alt, frame = 'altaz', unit = 'deg')
    #Tel.slew_radec(coordinate_radec, tracking = True)
    Tel.slew_altaz(alt = alt, az = az)
    #Tel.tracking_on()
    #Tel.tracking_off()
    #Tel.park()
    #Tel.disconnect()
