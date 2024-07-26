#%%
# Written by Hyeonho Choi 2023.02
import time
import pytz
import numpy as np
from astropy.time import Time
from datetime import datetime
from multiprocessing import Event
from multiprocessing import Lock

from alpaca.camera import Camera
from alpaca.camera import ImageArrayElementTypes
from alpaca.exceptions import *
from tcspy.utils.logger import mainLogger
from tcspy.utils import Timeout
from tcspy.utils.exception import *
from tcspy.configuration import mainConfig
#%%

class mainCamera(mainConfig):
    """
    This class provides control over an Alpaca camera connected to the system.
    
    Parameters
    ----------
    unitnum : int
        The unit number of the camera.

    Attributes
    ----------
    device : alpaca.camera.Camera
        The Alpaca camera device object.
    status : dict
        A dictionary containing the current status of the connected camera.

    Methods
    -------
    get_status() -> dict
        Get the current status of the connected camera.
    get_imginfo() -> tuple
        Get the image data and information from the connected camera.
    connect() -> None
        Connect to the camera and wait until the connection is established.
    disconnect() -> None
        Disconnect from the camera and wait until the disconnection is completed.
    set_binning(binning:int=1) -> None
        Set the binning for the connected camera.
    cooler_on(settemperature:float, tolerance:float=1) -> None
        Turn on the cooler for the connected camera and set the CCD temperature to the specified value.
    cooler_off(warmuptime:float=30) -> None
        Turn off the cooler for the connected camera and warm up the CCD for the specified duration.
    take_light(exptime:float, binning:int=1) -> tuple
        Capture a light frame with the connected camera.
    take_bias(binning:int=1) -> tuple
        Capture a bias frame with the connected camera.
    take_dark(exptime:float, binning:int=1) -> tuple
        Capture a dark frame with the connected camera.
    abort() -> None
        Aborts the current exposure.
    """
    
    def __init__(self,
                 unitnum : int,
                 **kwargs):
        
        super().__init__(unitnum=unitnum)
        self._unitnum = unitnum
        self.device = Camera(f"{self.config['CAMERA_HOSTIP']}:{self.config['CAMERA_PORTNUM']}",self.config['CAMERA_DEVICENUM'])
        self.status = self.get_status()
        self.cam_lock = Lock()
        self._log = mainLogger(unitnum = unitnum, logger_name = __name__+str(unitnum)).log()

    def get_status(self) -> dict:
        """
        Get the current status of the connected camera.

        Returns
        -------
        status : dict
            A dictionary containing the current status of the connected camera.
        """
        status = dict()
        status['update_time'] = Time.now().isot
        status['jd'] = None
        status['is_imgReady'] = None
        status['is_connected'] = False
        status['state'] = None
        status['name_cam'] = None
        status['numX'] = None
        status['numY'] = None
        status['maxADU'] = None
        status['binX'] = None
        status['binY'] = None
        status['fullwellcap'] = None
        status['readoutmode'] = None
        status['gain'] = None
        status['ccdtemp'] = None
        status['set_ccdtemp'] = None
        status['power_cooler'] = None
        status['name_sensor'] = None
        status['type_sensor'] = None
        
        # Update status
        if self.device.Connected:
            try:
                status['update_time'] = Time.now().isot
            except:
                pass
            try:
                status['jd'] = round(Time.now().jd,6)
            except:
                pass
            try:
                status['is_imgReady'] = self.device.ImageReady
            except:
                pass
            try:
                status['is_connected'] = self.device.Connected
            except:
                pass
            try:
                status['state'] = self.device.CameraState.name
            except:
                pass
            try:
                status['name_cam'] = self.device.Name
            except:
                pass
            try:
                status['numX'] = self.device.CameraXSize
            except:
                pass
            try:
                status['numY'] = self.device.CameraYSize
            except:
                pass
            try:
                status['maxADU'] = self.device.MaxADU
            except:
                pass
            try:
                status['binX'] = self.device.BinX
            except:
                pass
            try:
                status['binY'] = self.device.BinY
            except:
                pass
            try:
                status['fullwellcap'] = self.device.FullWellCapacity
            except:
                pass
            try:
                status['readoutmode'] = self.device.ReadoutMode
            except:
                pass
            try:
                status['gain'] = self.device.Gain
            except:
                pass
            try:
                status['egain'] = self.device.ElectronsPerADU
            except:
                pass
            try:
                status['ccdtemp'] = round(self.device.CCDTemperature,1)
            except:
                pass
            try:
                status['set_ccdtemp'] = round(self.device.SetCCDTemperature,1)
            except:
                pass
            try:
                status['power_cooler'] = round(self.device.CoolerPower,1)
            except:
                pass
            try:
                status['name_sensor'] = self.device.SensorName
            except:
                pass
            try:
                status['type_sensor'] = self.device.SensorType.name
            except:
                pass

        return status
    
    def get_imginfo(self) -> dict:
        """
        Get the image data and information from the connected camera.

        Returns
        -------
        imginfo : dict
            A dictionary containing the image data and information.
        status : dict
            A dictionary containing the current status of the connected camera.
        """
        status = self.get_status()
        imginfo = dict()
        imginfo['data'] = None
        imginfo['imgtype'] = None
        imginfo['numX'] = None
        imginfo['numY'] = None
        imginfo['numX'] = None
        imginfo['numY'] = None
        imginfo['binningX'] = None
        imginfo['binningY'] = None
        imginfo['numDimension'] = None
        imginfo['exptime'] = None
        imginfo['date_obs_ltc'] = None
        imginfo['date_obs_utc'] = None
        imginfo['jd'] = None
        imginfo['mjd'] = None
        
        if status['is_imgReady']:
            imgdata_alpaca =  self.device.ImageArray
            imginfo_alpaca = self.device.ImageArrayInfo
            if imginfo_alpaca.ImageElementType == ImageArrayElementTypes.Int32:
                if status['maxADU'] <= 65535:
                    img_dtype = np.uint16 
                else:
                    img_dtype = np.int32
            elif imginfo_alpaca.ImageElementType == ImageArrayElementTypes.Double:
                img_dtype = np.float64
            data = np.array(imgdata_alpaca, dtype=img_dtype).transpose()
            try:
                imginfo['data'] = data
            except:
                pass
            try:
                imginfo['imgtype'] = self.imgtype
            except:
                pass
            try:
                imginfo['numX'] = imginfo_alpaca.Dimension1
                imginfo['numY'] = imginfo_alpaca.Dimension2
            except:
                pass
            try:
                imginfo['binningX'] = status['numX']//imginfo_alpaca.Dimension1
                imginfo['binningY'] = status['numY']//imginfo_alpaca.Dimension2
            except:
                pass
            try:
                imginfo['numDimension'] = imginfo_alpaca.Rank
            except:
                pass
            try:
                imginfo['exptime'] = self.device.LastExposureDuration
            except:
                pass
            try:
                obstime_ut = Time(self.device.LastExposureStartTime).datetime
                tz_local = pytz.timezone(self.config['OBSERVER_TIMEZONE'])
                local_ut = pytz.utc.localize(obstime_ut)
                local_lt = local_ut.astimezone(tz_local)
                lt_str = local_lt.strftime("%Y-%m-%d %H:%M:%S")
                ut_str = local_ut.strftime("%Y-%m-%dT%H:%M:%S")
                lt = Time(lt_str, scale='local', format='iso')
                ut = Time(ut_str, scale='utc', format='isot')
                imginfo['date_obs_ltc'] = lt.iso
                imginfo['date_obs_utc'] = ut.isot
                imginfo['jd'] = ut.jd
                imginfo['mjd'] = ut.mjd
            except:
                pass
        return imginfo, status

    @Timeout(5, 'Timeout') 
    def connect(self):
        """
        Connect to the camera and wait until the connection is established.
        """
        self._log.info('Connecting to the Camera...')
        try:
            if not self.device.Connected:
                self.device.Connected = True
                time.sleep(float(self.config['CAMERA_CHECKTIME']))
            while not self.device.Connected:
                time.sleep(float(self.config['CAMERA_CHECKTIME']))
            if  self.device.Connected:
                self._log.info('Camera connected')
        except:
            self._log.critical('Connection failed')
            raise ConnectionError('Connection failed')
        return True
        
    
    @Timeout(5, 'Timeout')
    def disconnect(self):
        """
        Disconnect from the camera and wait until the disconnection is completed.
        """
        self._log.info('Disconnecting the camera...')
        try:
            if self.device.Connected:
                self.device.Connected = False
                time.sleep(float(self.config['CAMERA_CHECKTIME']))
            while self.device.Connected:
                time.sleep(float(self.config['CAMERA_CHECKTIME']))
            if not self.device.Connected:
                self._log.info('Camera disconnected')
        except:
            self._log.critical('Disconnect failed')
            raise ConnectionError('Connection failed')
        return True
            
    def cool(self,
             abort_action : Event,
             settemperature: float,
             tolerance: float = 1,
             max_consecutive_stable_iterations: int = 10,
             ):
        """
        Control the cooling process of the camera.

        Parameters
        ----------
        abort_action : threading.Event
            An event object used to abort the cooling process.
        settemperature : float
            The target temperature to cool the camera to.
        tolerance : float, optional
            The tolerance level for the temperature difference.
        max_consecutive_stable_iterations : int, optional
            The maximum number of consecutive stable iterations before considering the cooling process stalled.
        """
        try:
            if self.device.CanSetCCDTemperature:
                self.device.CoolerOn = True
                while not self.device.CoolerOn:
                    time.sleep(float(self.config['CAMERA_CHECKTIME']))
                self.device.SetCCDTemperature = settemperature
                self._log.info('Start cooling...')
                
                # Initialize variables for tracking temperature and gradient
                prev_temperature = self.device.CCDTemperature
                consecutive_stable_iterations = 0
                current_temperature = self.device.CCDTemperature

                while not np.abs(self.device.CCDTemperature - settemperature) < tolerance:
                    if abort_action.is_set():
                        self.device.CoolerOn = False
                        self._log.warning('Camera cooling is aborted')
                        raise AbortionException('Camera cooling is aborted')
                    current_temperature = self.device.CCDTemperature
                    cooler_power = None
                    if self.device.CanGetCoolerPower:
                        cooler_power = self.device.CoolerPower
                    
                    # Calculate the gradient
                    gradient = current_temperature - prev_temperature
                    
                    if gradient > -0.3:  # Adjust the threshold as needed
                        consecutive_stable_iterations += 1
                    else:
                        consecutive_stable_iterations = 0

                    # Check if the temperature has been stable for too long
                    if consecutive_stable_iterations >= max_consecutive_stable_iterations:
                        self._log.warning('{} CCD Temperature cannot be reached to the set temp, current temp: {}'.format(str(e), self.device.CCDTemperature))
                        raise CoolingFailedException('Cooling operation has stalled: camera cannot reach the set temperature')

                    self._log.info('Current temperature: %.1f [Power: %d]' % (current_temperature,cooler_power))
                    time.sleep(5)
                    
                    # Update the previous temperature for the next iteration
                    prev_temperature = current_temperature

                self._log.info('Cooling finished. Current temperature: %.1f' % self.device.CCDTemperature)
                return True
            else:
                self._log.critical('Cooling is not implemented on this device')
                raise CoolingFailedException('Cooling is not implemented on this device')
        except TimeoutError as e:
            self._log.warning('{} CCD Temperature cannot be reached to the set temp, current temp: {}'.format(str(e), self.device.CCDTemperature))
            raise CoolingFailedException('{} CCD Temperature cannot be reached to the set temp, current temp: {}'.format(str(e), self.device.CCDTemperature))
    
    def warm(self,
             abort_action : Event,
             settemperature : float = 10,
             tolerance: float = 1,
             max_consecutive_stable_iterations : int = 10
             ):
        """
        Control the warming process of the camera.

        Parameters
        ----------
        abort_action : threading.Event
            An event object used to abort the warming process.
        settemperature : float, optional
            The target temperature to warm the camera to.
        tolerance : float, optional
            The tolerance level for the temperature difference.
        max_consecutive_stable_iterations : int, optional
            The maximum number of consecutive stable iterations before considering the warming process stalled.
        """
        try:
            if self.device.CanSetCCDTemperature:
                self.device.SetCCDTemperature = settemperature
                self._log.info('Start warning...')
                
                # Initialize variables for tracking temperature and gradient
                prev_temperature = self.device.CCDTemperature
                consecutive_stable_iterations = 0
                current_temperature = self.device.CCDTemperature
                
                while not np.abs(self.device.CCDTemperature - settemperature) < tolerance:
                    if abort_action.is_set():
                        self.device.CoolerOn = False
                        self._log.warning('Camera warming is aborted')
                        raise AbortionException('Camera cooling is aborted')
                    current_temperature = self.device.CCDTemperature
                    cooler_power = None
                    if self.device.CanGetCoolerPower:
                        cooler_power = self.device.CoolerPower
                        
                    # Calculate the gradient
                    gradient = current_temperature - prev_temperature
                    
                    if gradient < 0.3:  # Adjust the threshold as needed
                        consecutive_stable_iterations += 1
                    else:
                        consecutive_stable_iterations = 0

                    # Check if the temperature has been stable for too long
                    if consecutive_stable_iterations >= max_consecutive_stable_iterations:
                        self._log.warning('{} CCD Temperature cannot be reached to the set temp, current temp: {}'.format(str(e), self.device.CCDTemperature))
                        break

                    self._log.info('Current temperature: %.1f [Power: %d]' % (current_temperature,cooler_power))
                    time.sleep(5)
                    
                    # Update the previous temperature for the next iteration
                    prev_temperature = current_temperature
                self.device.CoolerOn = False

                self._log.info('Warning finished. Current temperature: %.1f' % self.device.CCDTemperature)
                return True
            else:
                self._log.critical('Warming is not implemented on this device')
                raise WarmingFailedException('Warming is not implemented on this device')
        except TimeoutError as e:
            self._log.warning('{} CCD Temperature cannot be reached to the set temp, current temp: {}'.format(str(e), self.device.CCDTemperature))
            raise WarmingFailedException('{} CCD Temperature cannot be reached to the set temp, current temp: {}'.format(str(e), self.device.CCDTemperature))
    
    def exposure(self,
                 abort_action : Event,
                 exptime : float,
                 imgtype : str,
                 binning : int,
                 is_light : bool,
                 gain : int = 0
                 ):
        """
        Capture an image with the connected camera.

        Parameters
        ----------
        abort_action : threading.Event
            An event object used to abort the exposure process.
        exptime : float
            The exposure time for the image.
        imgtype : str
            The type of the image (e.g., 'light', 'bias', 'dark', 'flat').
        binning : int
            The binning value for the image.
        is_light : bool
            Whether the image is a light frame or not.
        gain : int, optional
            The gain value for the image.

        abort_action = Event()
        exptime = 10
        binning = 1
        imgtype = 'Light'
        gain = 2750
        
        Returns
        -------
        imginfo : dict
            A dictionary containing information about the captured image.
        """
        # Set Gain
        self.cam_lock.acquire()
        try:
            self._update_gain(gain = gain)
            
            # Set binning 
            self._set_binning(binning = binning)
            self.imgtype = imgtype.upper()

            # Set minimum exposure time
            if exptime < self.device.ExposureMin:
                exptime = self.device.ExposureMin
            
            # Set imagetype & exposure time & is_light
            if not imgtype.upper() in ['BIAS', 'DARK', 'FLAT', 'LIGHT']:
                self._log.critical(f'Type "{imgtype}" is not set as imagetype')
                self.cam_lock.release()
                raise ExposureFailedException(f'Type "{imgtype}" is not set as imagetype')
            
            # Exposure
            self._log.info('Start exposure...')
            self.device.StartExposure(Duration = exptime, Light = is_light)
            while not self.device.ImageReady:
                if abort_action.is_set():
                    self.cam_lock.release()
                    self.abort()
                time.sleep(float(self.config['CAMERA_CHECKTIME']))
                
            imginfo, status = self.get_imginfo()

            # Modify image information if camera returns too detailed exposure time
            imginfo['exptime'] = round(float(imginfo['exptime']),1)
            self._log.info('Exposure finished')
            return imginfo 
        
        finally:
            self.cam_lock.release()

    def abort(self):
        """
        Aborts the current exposure.
        """
        self.cam_lock.acquire()
        self._log.warning('Camera exposure is aborted')
        try:
            if self.device.CanAbortExposure:
                self.device.AbortExposure()
        finally:
            self.cam_lock.release()
            raise AbortionException('Camera exposure is aborted')
    
    def _update_gain(self,
                    gain : int = 0):
        try:
            if self.device.Gain != gain:
                self.device.Gain = gain
            else:
                pass
        except NotImplementedException as e:
            self._log.critical(e)
            pass
        
    def _set_binning(self,
                     binning :int = 1):
        if (binning > self.device.MaxBinX) | (binning > self.device.MaxBinY):
            logtxt = 'binning value %d above the maximum supported %d'%(binning, self.device.MaxBinX)
            self._log.warning(logtxt) 
            raise ValueError(logtxt)
        self.device.StartX = 0
        self.device.StartY = 0
        self.device.BinX = self.device.BinY = binning
        self.device.NumX = self.device.CameraXSize // self.device.BinX
        self.device.NumY = self.device.CameraYSize // self.device.BinY
        #self.status = self.get_status()
# %% Test
if __name__ == '__main__':
    import numpy as np
    import matplotlib.pyplot as plt
    A = mainCamera(unitnum = 2)
    abort_action = Event()
    #C = A.exposure(exptime = 10, imgtype = 'Light', abort_action= abort_action, binning = 1, is_light = False)
    from multiprocessing import Process
    p = Process(target = A.exposure, kwargs = dict(exptime = 10, imgtype = 'Dark', abort_action= abort_action, binning = 1, is_light = False))
    p.start()