#%%
# Written by Hyeonho Choi 2023.02
import time
import pytz
import numpy as np
from astropy.time import Time
from datetime import datetime
from threading import Event

from alpaca.camera import Camera
from alpaca.camera import ImageArrayElementTypes
from tcspy.utils.logger import mainLogger
from tcspy.utils import Timeout
from tcspy.utils.exception import *
from tcspy.configuration import mainConfig


#%%

class mainCamera(mainConfig):
    """
    This class provides control over an Alpaca camera connected to the system.
    
    Parameters
    ==========
    1. device : alpaca.camera.Camera
        The camera object to control.

    Methods
    =======
    1. get_status() -> dict
        Get the current status of the connected camera.
    2. get_imginfo() -> tuple
        Get the image data and information from the connected camera.
    3. connect() -> None
        Connect to the camera and wait until the connection is established.
    4. disconnect() -> None
        Disconnect from the camera and wait until the disconnection is completed.
    5. set_binning(binning:int=1) -> None
        Set the binning for the connected camera.
    6. cooler_on(settemperature:float, tolerance:float=1) -> None
        Turn on the cooler for the connected camera and set the CCD temperature to the specified value.
    7. cooler_off(warmuptime:float=30) -> None
        Turn off the cooler for the connected camera and warm up the CCD for the specified duration.
    8. take_light(exptime:float, binning:int=1) -> tuple
        Capture a light frame with the connected camera.
    9. take_bias(binning:int=1) -> tuple
        Capture a bias frame with the connected camera.
    10. take_dark(exptime:float, binning:int=1) -> tuple
        Capture a dark frame with the connected camera.
    11. abort() -> None
        Aborts the current exposure.
    """
    
    def __init__(self,
                 unitnum : int,
                 **kwargs):
        
        super().__init__(unitnum=unitnum)
        self._unitnum = unitnum
        self._log = mainLogger(unitnum = unitnum, logger_name = __name__+str(unitnum)).log()
        self._checktime = float(self.config['CAMERA_CHECKTIME'])
        self.device = Camera(f"{self.config['CAMERA_HOSTIP']}:{self.config['CAMERA_PORTNUM']}",self.config['CAMERA_DEVICENUM'])
        self.status = self.get_status()

    def get_status(self) -> dict:
        """
        Get the current status of the connected camera.

        Returns
        =======
        1. status : dict
            A dictionary containing the following information about the connected camera:
            - 'update_time': Time stamp of the status update in ISO format.
            - 'jd': Julian date of the status update, rounded to six decimal places.
            - 'is_imgReady': Whether the camera is ready to capture an image.
            - 'is_connected': Whether the camera is connected.
            - 'state': The current state of the camera.
            - 'name_cam': The name of the camera.
            - 'numX': The width of the camera sensor in pixels.
            - 'numY': The height of the camera sensor in pixels.
            - 'maxADU': The maximum analog-to-digital unit of the camera.
            - 'binX': The binning factor in the X direction.
            - 'binY': The binning factor in the Y direction.
            - 'fullwellcap': The full well capacity of the camera.
            - 'readoutmode': The current readout mode of the camera.
            - 'gain': The current gain of the camera.
            - 'ccdtemp': The current temperature of the camera sensor.
            - 'power_cooler': The current power level of the camera cooler.
            - 'name_sensor': The name of the camera sensor.
            - 'type_sensor': The type of the camera sensor.
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
                status['ccdtemp'] = round(self.device.CCDTemperature,1)
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
        =======
        1. imginfo : dict
            A dictionary containing the following information about the captured image:
            - 'data': The numpy array containing the image data.
            - 'imgtype' : The type of the image (object, bias, dark, flat)
            - 'numX': The width of the image.
            - 'numY': The height of the image.
            - 'binning' : The binning of the image. 
            - 'numDimension': The number of dimensions of the image.
            - 'exptime': The exposure time of the last captured image.
            - 'date_obs': The start time of the last captured image.
        2. status : dict
            A dictionary containing the current status of the connected camera, as returned by get_status().

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
        imginfo['date_obs_utc'] = Time.now().isot
        imginfo['jd'] = round(Time.now().jd,6)
        
        if status['is_imgReady']:
            imgdata_alpaca =  self.device.ImageArray
            imginfo_alpaca = self.device.ImageArrayInfo
            if imginfo_alpaca.ImageElementType == ImageArrayElementTypes.Int32:
                if status['maxADU'] <= 65535:
                    img_dtype = np.int16 
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
                time.sleep(self._checktime)
            while not self.device.Connected:
                time.sleep(self._checktime)
            if  self.device.Connected:
                self._log.info('Camera connected')
        except:
            self._log.warning('Connection failed')
            raise ConnectionError('Connection failed')
        return True
        
    
    @Timeout(5, 'Timeout')
    def disconnect(self):
        """
        Disconnect from the camera and wait until the disconnection is completed.
        """
        
        self._log.info('Disconnecting camera...')
        try:
            if self.device.Connected:
                self.device.Connected = False
                time.sleep(self._checktime)
            while self.device.Connected:
                time.sleep(self._checktime)
            if not self.device.Connected:
                self._log.info('Camera disconnected')
        except:
            self._log.warning('Disconnect failed')
            raise ConnectionError('Connection failed')
        return True
    
    def cooler_on(self):
        if self.device.CanSetCCDTemperature:
            self.device.CoolerOn = True
        else:
            raise CoolingFailedException()
        return True

    def cooler_off(self):
        if self.device.CanSetCCDTemperature:
            self.device.CoolerOn = False
        else:
            raise CoolingFailedException()
        return True
            
    def cool(self,
             abort_action : Event,
             settemperature: float,
             tolerance: float = 1,
             max_consecutive_stable_iterations: int = 10,
             ):
        try:
            if self.device.CanSetCCDTemperature:
                self.device.CoolerOn = True
                while not self.device.CoolerOn:
                    time.sleep(self._checktime)
                self.device.SetCCDTemperature = settemperature
                self._log.info('Start cooling...')
                
                # Initialize variables for tracking temperature and gradient
                prev_temperature = self.device.CCDTemperature
                consecutive_stable_iterations = 0
                current_temperature = self.device.CCDTemperature

                while not self.device.CCDTemperature - settemperature < tolerance:
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
                    
                    if gradient > -0.1:  # Adjust the threshold as needed
                        consecutive_stable_iterations += 1
                    else:
                        consecutive_stable_iterations = 0

                    # Check if the temperature has been stable for too long
                    if consecutive_stable_iterations >= max_consecutive_stable_iterations:
                        self._log.critical('Cooling operation has stalled')
                        raise CoolingFailedException('Cooling operation has stalled')

                    self._log.info('Current temperature: %.1f [Power: %d]' % (current_temperature,cooler_power))
                    time.sleep(5)
                    
                    # Update the previous temperature for the next iteration
                    prev_temperature = current_temperature

                self._log.info('Cooling finished. Current temperature: %.1f' % current_temperature)
                return True
            else:
                self._log.warning('Cooling is not implemented on this device')
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
        Turn off the cooler for the connected camera and warm up the CCD for the specified duration.

        Parameters
        ==========
        1. warmuptime : float, optional
            The duration to warm up the CCD, in seconds.
        """
        try:
            if self.device.CanSetCCDTemperature:
                self.device.SetCCDTemperature = settemperature
                self._log.info('Start warning...')
                
                # Initialize variables for tracking temperature and gradient
                prev_temperature = self.device.CCDTemperature
                consecutive_stable_iterations = 0
                current_temperature = self.device.CCDTemperature
                
                while not self.device.CCDTemperature - settemperature > tolerance:
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
                    
                    if gradient < 0.1:  # Adjust the threshold as needed
                        consecutive_stable_iterations += 1
                    else:
                        consecutive_stable_iterations = 0

                    # Check if the temperature has been stable for too long
                    if consecutive_stable_iterations >= max_consecutive_stable_iterations:
                        self._log.critical('Warming operation has stalled')
                        raise WarmingFailedException('Warming operation has stalled')

                    self._log.info('Current temperature: %.1f [Power: %d]' % (current_temperature,cooler_power))
                    time.sleep(5)
                    
                    # Update the previous temperature for the next iteration
                    prev_temperature = current_temperature
                self.device.CoolerOn = False

                self._log.info('Warning finished. Current temperature: %.1f' % current_temperature)
                return True
            else:
                self._log.warning('Warming is not implemented on this device')
                raise WarmingFailedException('Warming is not implemented on this device')
        except TimeoutError as e:
            self._log.warning('{} CCD Temperature cannot be reached to the set temp, current temp: {}'.format(str(e), self.device.CCDTemperature))
            raise WarmingFailedException('{} CCD Temperature cannot be reached to the set temp, current temp: {}'.format(str(e), self.device.CCDTemperature))
    
    def exposure(self,
                 abort_action : Event,
                 exptime : float,
                 imgtype : str,
                 binning : int,
                 is_light : bool
                 ):
        """
        Capture a light frame with the connected camera.

        Parameters
        ==========
        1. exptime : float (default = minimun exposure time of a CCD)
            The exposure time for the light frame, in seconds.
        2. imgtypename : str (default = 'object)
            The type of an image
        3. binning : int (default = 1)
            The binning value to use for the light frame.
        

        Returns
        =======
        1. imginfo : dict
            A dictionary containing the following information about the captured image, as returned by get_imginfo()
        """
        
        # Set binning 
        self._set_binning(binning = binning)
        self.imgtype = imgtype.upper()
        
        # Set minimum exposure time
        if exptime < self.device.ExposureMin:
            exptime = self.device.ExposureMin
        
        # Set imagetype & exposure time & is_light
        if not imgtype.upper() in ['BIAS', 'DARK', 'FLAT', 'LIGHT']:
            self._log.critical(f'Type "{imgtype}" is not set as imagetype')
            raise ExposureFailedException(f'Type "{imgtype}" is not set as imagetype')

        # Exposure
        self.device.StartExposure(Duration = exptime, Light = is_light)
        time.sleep(self._checktime)
        while not self.device.ImageReady:
            if abort_action.is_set():
                self._log.warning('Camera exposure is aborted')
                self.abort()
                raise AbortionException('Camera exposure is aborted')
            time.sleep(self._checktime)
        imginfo, status = self.get_imginfo()
        # Modify image information if camera returns too detailed exposure time
        imginfo['exptime'] = round(float(imginfo['exptime']),1)
        #imginfo['exptime'] = exptime
        return imginfo 

    def abort(self):
        """
        Aborts the current exposure.
        """
        if self.device.CanAbortExposure:
            self.device.AbortExposure()
    
    def _set_binning(self,
                     binning :int = 1):
        """
        Set the binning for the connected camera.

        Parameters
        ==========
        1. binning : int, optional
            The binning value to set. Must be less than or equal to the maximum supported binning values for both X and Y.
        """
        
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
    A = mainCamera(unitnum = 1)
    A.connect()

    C = A.exposure(exptime = 0, imgtype = 'bias', abort_action= Event(), binning = 1, is_light = False)
    
    #%%
    data = np.array(imginfo['data'])
    plt.figure(dpi = 300)
    plt.imshow(data, vmin = 100, vmax= 150)
    plt.colorbar()
    plt.show()

#%%
    #A.cooler_off(warmuptime=10)
    A.disconnect()
# %%
