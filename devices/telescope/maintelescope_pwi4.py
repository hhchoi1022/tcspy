#%%
# Other modules
from astropy.coordinates import SkyCoord
import time
from astropy.time import Time

from tcspy.devices.telescope.pwi4_client import PWI4 # PWI4 API 
from tcspy.configuration import mainConfig
from tcspy.devices.observer import mainObserver
from tcspy.utils.logger import mainLogger
from tcspy.utils import to_SkyCoord
from tcspy.utils import Timeout
from tcspy.utils.target import mainTarget
#%%

class mainTelescope_pwi4(mainConfig):
    """
    A class representing a telescope that uses the PWI4 protocol.

    Parameters
    ==========
    1. Observer : mainObserver, optional
        An instance of the mainObserver class used for observation. If None, a new instance is created using the mainConfig object.

    Methods
    =======
    1. get_status() -> dict
        Get the current status of the telescope.
    2. connect()
        Connect to the telescope.
    3. disconnect()
        Disconnect from the telescope.
    4. set_park(altitude : float = 40, azimuth : float = 180) -> None
        Set the park position of the telescope
    5. park()
        Park the telescope.
    6. unpark()
        Unpark the telescope.
    7. find_home()
        Find the home position of the telescope.
    8. slew_radec(coordinate : SkyCoord = None, ra : float = None, dec : float = None, target_name : str = '', tracking = True)
        Slew the telescope to a specified RA/Dec coordinate.
    9. slew_altaz(coordinate : SkyCoord = None, alt : float = None, az : float = None, tracking = False)
        Slews the telescope to the specified Alt-Azimuth coordinate.
    10. tracking_on()
        Activates the tracking mode of the mount.
    11. tracking_off()
        Deactivates the tracking mode of the mount.
    12. abort()
        Abort the movement of the mount
    """

    def __init__(self,
                 unitnum : int,
                 **kwargs):
        
        super().__init__(unitnum = unitnum)
        self._unitnum = unitnum
        self._log = mainLogger(unitnum = unitnum, logger_name = __name__+str(unitnum)).log()
        self._min_altitude = float(self.config['TARGET_MINALT'])
        self._max_altitude = float(self.config['TARGET_MAXALT'])
        self._checktime = float(self.config['TELESCOPE_CHECKTIME'])
        self.observer = mainObserver(unitnum = unitnum)
        self.device = PWI4(self.config['TELESCOPE_HOSTIP'], self.config['TELESCOPE_PORTNUM'])
        self.PWI_status = self.device.status()
        self.status = self.get_status()
        self.condition = 'idle'
        
    def get_status(self):
        """
        Get the current status of the telescope.

        Returns
        =======
        1. status : dict
            A dictionary containing the following keys:
            - 'update_time' : The timestamp of the last update.
            - 'jd' : The Julian Date.
            - 'ra' : The Right Ascension in J2000 epoch, in hours.
            - 'dec' : The Declination in J2000 epoch, in degrees.
            - 'alt' : The altitude of the telescope, in degrees.
            - 'az' : The azimuth of the telescope, in degrees.
            - 'at_parked' : True if the telescope is currently parked, False otherwise.
            - 'at_home' : None.
            - 'is_connected' : True if the telescope is connected, False otherwise.
            - 'is_tracking' : True if the telescope is currently tracking, False otherwise.
            - 'is_slewing' : True if the telescope is currently slewing, False otherwise.
            - 'is_stationary' : True if the telescope is currently stationary, False otherwise.
            - 'axis1_rms' : The RMS error of axis 1 in arcseconds.
            - 'axis2_rms' : The RMS error of axis 2 in arcseconds.
            - 'axis1_maxvel' : The maximum velocity of axis 1 in degrees per second.
            - 'axis2_maxvel' : The maximum velocity of axis 2 in degrees per second.
        """
        
        status = dict()
        status['update_time'] = Time.now().isot
        status['jd'] = "{:.6f}".format(Time.now().jd)
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
        status['axis1_rms'] = None
        status['axis2_rms'] = None
        status['axis1_maxvel'] = None
        status['axis2_maxvel'] = None
        try:
            if self.PWI_status.mount.is_connected:
                self._update_PWI_status()
                status['update_time'] = self.PWI_status.response.timestamp_utc
                status['jd'] = "{:.6f}".format(self.PWI_status.mount.julian_date)
                status['ra'] = "{:.4f}".format(self.PWI_status.mount.ra_j2000_hours)
                status['dec'] = "{:.4f}".format(self.PWI_status.mount.dec_j2000_degs)
                status['alt'] = "{:.3f}".format(self.PWI_status.mount.altitude_degs)
                status['az'] = "{:.3f}".format(self.PWI_status.mount.azimuth_degs)
                status['at_parked'] = False
                status['at_home'] = None
                status['is_connected'] = self.PWI_status.mount.is_connected
                status['is_tracking'] = self.PWI_status.mount.is_tracking
                status['is_slewing'] = self.PWI_status.mount.is_slewing 
                status['is_stationary'] = (self.PWI_status.mount.axis0.rms_error_arcsec < self.config['TELESCOPE_RMSRA']) & (self.PWI_status.mount.axis1.rms_error_arcsec < self.config['TELESCOPE_RMSDEC']) & (not self.PWI_status.mount.is_slewing)
                status['axis1_rms'] = "{:.4f}".format(self.PWI_status.mount.axis0.rms_error_arcsec)
                status['axis2_rms'] = "{:.4f}".format(self.PWI_status.mount.axis1.rms_error_arcsec)
                status['axis1_maxvel'] = "{:.4f}".format(self.PWI_status.mount.axis0.max_velocity_degs_per_sec)
                status['axis2_maxvel'] = "{:.4f}".format(self.PWI_status.mount.axis1.max_velocity_degs_per_sec)
        except:
            pass
        return status
    
    def _update_PWI_status(self):
        """
        Update the status of the telescope.
        """
        
        self.PWI_status = self.device.status()
    
    @Timeout(5, 'Timeout')
    def connect(self):
        """
        Connect to the telescope.
        """
        
        self._log.info('Connecting to the telescope...')
        try:
            self._update_PWI_status()
            if not self.PWI_status.mount.is_connected:
                self.PWI_status = self.device.mount_connect()
            while not self.PWI_status.mount.is_connected:
                time.sleep(self._checktime)
                self._update_PWI_status()
            self._log.info('Telescope connected')
        except:
            self._log.warning('Connection failed')
        self._update_PWI_status()
        self.status = self.get_status()
    
    def disconnect(self):
        """
        Disconnect from the telescope.
        """
        
        self._log.info('Disconnecting the telescope...')
        self.device.mount_disconnect()
        self._update_PWI_status()
        if self.PWI_status.mount.is_connected:
            self.PWI_status = self.device.mount_disconnect()
        while self.PWI_status.mount.is_connected:
            time.sleep(self._checktime)
            self._update_PWI_status()
        self._log.info('Telescope disconnected')
        self._update_PWI_status()
        self.status = self.get_status()
    '''    
    def set_park(self,
                 altitude : float = 40,
                 azimuth : float = 180):
        """
        Set the park position of the telescope.

        Parameters
        ==========
        1. altitude : float, optional
            The altitude of the park position, in degrees. Only used if coordinate is not specified.
        2. azimuth : float, optional
            The azimuth of the park position, in degrees. Only used if coordinate is not specified.
        """
        coordinate = SkyCoord(azimuth, altitude, frame = 'altaz', unit ='deg')
        alt = coordinate.alt.deg
        az = coordinate.az.deg
        self._log.info('Setting park position of the telescope... Slew to the park position (Alt = %.1f Az = %.1f)'%(alt, az))
        
        self.slew_altaz(alt = alt, az = az, tracking = False)
        self.status = self.get_status()
        time.sleep(5*self._checktime)
        while not self.status['is_stationary']:
            time.sleep(self._checktime)
            self.status = self.get_status()
        self.device.mount_set_park_here()
        self.status = self.get_status()
        self._log.info('Park position is set (Alt = %.1f Az = %.1f)'%(alt, az))
        '''
    def park(self):
        """
        Parks the telescope.
        """
        coordinate = SkyCoord(self.config['TELESCOPE_PARKAZ'],self.config['TELESCOPE_PARKALT'], frame = 'altaz', unit ='deg')
        alt = coordinate.alt.deg
        az = coordinate.az.deg
        
        #if self.device.CanPark:
            #if not self.device.AtPark:

        self._log.info('Parking telescope...')
        self.unpark()
        #self.status = self.get_status()
        self.condition = 'slewing'
        self.device.mount_goto_alt_az(alt_degs = alt, az_degs = az)
        self.status = self.get_status()
        while not self.status['is_stationary']:
            time.sleep(self._checktime)
            self.status = self.get_status()
        self.condition = 'idle'
        self.status = self.get_status()
        self._log.info('Telescope parked')
    '''
    def park(self):
        """
        Park the telescope.
        """
        
        self._log.info('Parking telescope...')
        self.device.mount_park()
        time.sleep(5*self._checktime)
        self.status = self.get_status()
        while not self.status['is_stationary']:
            time.sleep(self._checktime)
            self.status = self.get_status()
        self._log.info('Telescope parked')
    '''
    def unpark(self):
        """
        Unpark the telescope.
        """
        
        self._log.info('Unparking telescope...')
        self.status = self.get_status()
        self._update_PWI_status()
        if not self.PWI_status.mount.axis0.is_enabled:
            self.device.mount_enable(axisNum = 0)
        if not self.PWI_status.mount.axis1.is_enabled:
            self.device.mount_enable(axisNum = 1)
        self.status = self.get_status()
        self._log.info('Telescope unparked')
    
    def find_home(self):
        """
        Find the home position of the telescope.
        """
        
        self._log.info('Finding home position...')
        self.condition = 'slewing'
        self.device.mount_find_home()
        self.status = self.get_status()
        time.sleep(5*self._checktime)
        while not self.status['is_stationary']:
            time.sleep(self._checktime)
            self.status = self.get_status()
        self.condition = 'idle'
        self.status = self.get_status()
        self._log.info('Finding home finished')

    def slew_radec(self,
                   coordinate : SkyCoord = None,
                   ra : float = None,
                   dec : float = None,
                   target_name : str = '',
                   tracking = True):
        """
        Slew the telescope to a specified RA/Dec coordinate.

        Parameters
        ==========
        1. coordinate : SkyCoord, optional
            The coordinate of the target, in SkyCoord format. If not specified, ra and dec must be specified.
        2. ra : float, optional
            The Right Ascension of the target, in decimal hours. Only used if coordinate is not specified.
        3. dec : float, optional
            The Declination of the target, in decimal degrees. Only used if coordinate is not specified.
        4. target_name : str, optional
            The name of the target.
        5. tracking : bool, optional
            Whether to turn tracking on after slewing
        """
        
        if (ra != None) & (dec != None):
            coordinate = to_SkyCoord(ra, dec)
        ra = coordinate.ra.hour
        dec = coordinate.dec.deg
        target = mainTarget(unitnum = self._unitnum, observer = self.observer, target_ra = ra, target_dec = dec, target_name = target_name)
        altaz = target.altaz()
        self._log.info('Slewing to the coordinate (RA = %.3f, Dec = %.3f, Alt = %.1f, Az = %.1f)' %(ra, dec, altaz.alt.deg, altaz.az.deg))

        # Check coordinates
        if altaz.alt.deg < self._min_altitude:
            self._log.critical('Destination altitude below limit (%.1fdeg)' %altaz.alt.deg)
            raise ValueError('Destination altitude below limit (%.1fdeg)' %altaz.alt.deg)
        
        # Slewing 
        self.unpark()
        #self.status = self.get_status()
        self.condition = 'slewing'
        self.device.mount_goto_ra_dec_j2000(ra, dec)
        time.sleep(5*self._checktime)
        self.status = self.get_status()
        while not self.status['is_stationary']:
            time.sleep(self._checktime)
            self.status = self.get_status()
        time.sleep(2*self._checktime)
        self.condition = 'idle'
        self.status = self.get_status()
        self._log.info('Slewing finished. Current coordinate (RA = %.3f, Dec = %.3f, Alt = %.1f, Az = %.1f)' %(self.status['ra'], self.status['dec'], self.status['alt'], self.status['az']))
        if not tracking:
            self.tracking_off()
    
    def slew_altaz(self,
                   coordinate : SkyCoord = None,
                   alt : float = None,
                   az : float = None,
                   tracking = False):
        """
        Slews the telescope to the specified Alt-Azimuth coordinate.

        Parameters
        ==========
        1. coordinate : `~astropy.coordinates.SkyCoord`, optional
            The target Alt-Azimuth coordinate to slew to.
        2. alt : float, optional
            The target altitude in degrees.
        3. az : float, optional
            The target azimuth in degrees.
        4. tracking : bool, optional
            If True, tracking will be enabled after slewing.
        """
     
        if coordinate == None:
            coordinate = SkyCoord(az, alt, frame = 'altaz', unit ='deg')
        alt = coordinate.alt.deg
        az = coordinate.az.deg
        self._log.info('Slewing to the coordinate (Alt = %.1f, Az = %.1f)' %(alt, az))
        
        # Check coordinates
        if alt < self._min_altitude:
            self._log.critical('Destination altitude below limit (%.1fdeg)' %alt)
            raise ValueError('Destination altitude below limit (%.1fdeg)' %alt)

        # Slewing 
        self.unpark()
        #self.status = self.get_status()
        self.condition = 'slewing'
        self.device.mount_goto_alt_az(alt_degs = alt, az_degs = az)
        time.sleep(5*self._checktime)
        self.status = self.get_status()
        while not self.status['is_stationary']:
            time.sleep(self._checktime)
            self.status = self.get_status()
        time.sleep(2*self._checktime)
        self.condition = 'idle'
        self.status = self.get_status()
        self._log.info('Slewing finished. Current coordinate (Alt = %.1f, Az = %.1f)' %(self.status['alt'], self.status['az']))
        if tracking:
            self.tracking_on()
    
    def tracking_on(self):
        """
        Activates the tracking mode of the mount.
        """
        
        self.status = self.get_status()
        if not self.status['is_tracking']:
            self.device.mount_tracking_on()
            self._log.info('Tracking activated')
        else:
            self._log.critical('Tracking failed')
            raise SystemError('Tracking failed')
        self.status = self.get_status()
        
    def tracking_off(self):
        """
        Deactivates the tracking mode of the mount.
        """
        
        self.status = self.get_status()
        if self.status['is_tracking']:
            self.device.mount_tracking_off()
            self._log.info('Tracking deactivated')
        else:
            self._log.critical('Untracking failed')
            raise SystemError('Untracking failed')
        self.status = self.get_status()
        
    def abort(self):
        """
        Abort the movement of the mount
        """
        
        self.device.mount_stop()
        self.condition = 'idle'
        self._log.warning('Telescope aborted')
        self.status = self.get_status()
    

# %%
if __name__ == '__main__':
    config = mainConfig().config
    config['TELESCOPE_PORTNUM'] = 8220
    device = PWI4(config['TELESCOPE_HOSTIP'], config['TELESCOPE_PORTNUM'])
    Tel = mainTelescope_pwi4(device = device, observer = mainObserver(**config))
#%%