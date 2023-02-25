

#%%


import time
import numpy as np
from astropy.io import fits
from astropy.time import Time
from progress.bar import Bar

import alpaca
from alpaca.camera import Camera
from alpaca.camera import ImageArrayElementTypes

from tcspy.utils import mainLogger
from tcspy.utils import Timeout
from tcspy.configuration import mainConfig

#%%

log = mainLogger(__name__).log()
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
                 device : alpaca.camera.Camera):
        
        super().__init__()
        self._checktime = float(self.config['CAMERA_CHECKTIME'])
        
        if isinstance(device, alpaca.camera.Camera):
            self.device = device
            self.status = self.get_status()

        else:
            log.warning('Device type is not mathced to Alpaca Camera')
            raise ValueError('Device type is not mathced to Alpaca Camera')
 
    def get_status(self) -> dict:
        """
        Get the current status of the connected camera.

        Returns
        =======
        1. status : dict
            A dictionary containing the following information about the connected camera:
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
        status['update_time'] = Time.now().iso
        status['jd'] = None
        status['is_imgReady'] = None
        status['is_connected'] = None
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
        try:
            if self.device.Connected:
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
            imginfo['data'] = data
            imginfo['imgtype'] = self._imagetype
            imginfo['numX'] = imginfo_alpaca.Dimension1
            imginfo['numY'] = imginfo_alpaca.Dimension2
            imginfo['binningX'] = status['numX']//imginfo_alpaca.Dimension1
            imginfo['binningY'] = status['numY']//imginfo_alpaca.Dimension2
            imginfo['numDimension'] = imginfo_alpaca.Rank
            imginfo['exptime'] = self.device.LastExposureDuration
            imginfo['date_obs'] = self.device.LastExposureStartTime
            imginfo['jd'] = Time(self.device.LastExposureStartTime).jd
        else:
            pass
        return imginfo, status

    @Timeout(5, 'Timeout') 
    def connect(self):
        """
        Connect to the camera and wait until the connection is established.
        """
        
        log.info('Connecting to the Camera...')
        try:
            if not self.device.Connected:
                self.device.Connected = True
            while not self.device.Connected:
                time.sleep(self._checktime)
            if  self.device.Connected:
                log.info('Camera connected')
        except:
            log.warning('Connection failed')
        self.status = self.get_status()

    def disconnect(self):
        """
        Disconnect from the camera and wait until the disconnection is completed.
        """
        
        self.device.Connected = False
        log.info('Disconnecting to the Camera...')
        while self.device.Connected:
            time.sleep(self._checktime)
        if not self.device.Connected:
            log.info('Camera disconnected')
        self.status = self.get_status()
            
    def set_binning(self,
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
            log.warning(logtxt) 
            raise ValueError(logtxt)
        self.device.StartX = 0
        self.device.StartY = 0
        self.device.BinX = self.device.BinY = binning
        self.device.NumX = self.device.CameraXSize // self.device.BinX
        self.device.NumY = self.device.CameraYSize // self.device.BinY
        self.status = self.get_status()
    
    @Timeout(30, 'Timeout') 
    def cooler_on(self,
                  settemperature : float,
                  tolerance : float = 1):
        """
        Turn on the cooler for the connected camera and set the CCD temperature to the specified value.

        Parameters
        ==========
        1. settemperature : float
            The target CCD temperature to set.
        2. tolerance : float, optional
            The tolerance level for the CCD temperature. The cooling process will end when the temperature is within this tolerance of the target temperature.
        """
        try:
            if self.device.CanSetCCDTemperature:
                self.device.SetCCDTemperature = settemperature
                self.device.CoolerOn = True
                log.info('Start cooling...')
                while not self.device.CCDTemperature - settemperature < tolerance:
                    log.info('Current temperature : %.1f'%(self.device.CCDTemperature))
                    time.sleep(5)
                log.info('Cooling finished. Set temperature : %.1f'%(settemperature))
            else:
                log.warning('Cooling is not implemented on this device')
        except TimeoutError as e:
            log.warning('{}CCD Temperature cannot be reached to the set temp, current temp : {}'.format(str(e), self.device.CCDTemperature))
            
    
    def cooler_off(self,
                   warmuptime : float = 30):
        """
        Turn off the cooler for the connected camera and warm up the CCD for the specified duration.

        Parameters
        ==========
        1. warmuptime : float, optional
            The duration to warm up the CCD, in seconds.
        """
        
        if self.device.CoolerOn:
            self.device.SetCCDTemperature = 10
            log.info('Warming up...')
            idx = warmuptime//5
            for i in range(idx):
                log.info('Current temperature : %.1f'%(self.device.CCDTemperature))
                time.sleep(5)
            self.device.CoolerOn = False
            log.info('Cooler is now off')
        self.status = self.get_status()
            
    def take_light(self,
                   exptime : float,
                   binning : int = 1,
                   imgtypename : str = 'object'
                   ):
        """
        Capture a light frame with the connected camera.

        Parameters
        ==========
        1. exptime : float
            The exposure time for the light frame, in seconds.
        2. binning : int, optional
            The binning value to use for the light frame.

        Returns
        =======
        1. imginfo : dict
            A dictionary containing the following information about the captured image, as returned by get_imginfo()
        2. status : dict
            A dictionary containing the current status of the connected camera, as returned by get_status()
        """
        self._imagetype = imgtypename
        self.set_binning(binning = binning)
        log.info('[LIGHT] Start exposure (exptime = %.1f)'%exptime)
        self.device.StartExposure(Duration = exptime, Light = True)
        time.sleep(2*self._checktime)
        while not self.device.ImageReady :
            time.sleep(self._checktime)
        imginfo, status = self.get_imginfo()
        log.info(f'[{imgtypename.upper()}] Exposure finished (exptime = %.1f)'%exptime)
        self.status = self.get_status()
        return imginfo, status
        
    def take_bias(self,
                  binning : int = 1,
                  imgtypename : str = 'bias'
                  ):
        """
        Capture a bias frame with the connected camera.

        Parameters
        ==========
        1. binning : int, optional
            The binning value to use for the bias frame.

        Returns
        =======
        1. imginfo : dict
            A dictionary containing the following information about the captured image, as returned by get_imginfo()
        2. status : dict
            A dictionary containing the current status of the connected camera, as returned by get_status().
        """
        self._imagetype = imgtypename
        self.set_binning(binning = binning)
        log.info('[BIAS] Start exposure for bias')
        self.device.StartExposure(Duration = self.device.ExposureMin, Light = False)
        time.sleep(2*self._checktime)
        while not self.device.ImageReady:
            time.sleep(self._checktime)
        imginfo, status = self.get_imginfo()
        log.info(f'[{imgtypename.upper()}] Exposure finished')
        return imginfo, status

    def take_dark(self,
                  exptime : float,
                  binning : int = 1,
                  imgtypename : str = 'dark'
                  ):
        """
        Capture a dark frame with the connected camera.

        Parameters
        ==========
        1. exptime : float
            The exposure time for the dark frame, in seconds.
        2. binning : int, optional
            The binning value to use for the dark frame.

        Returns
        =======
        1. imginfo : dict
            A dictionary containing the following information about the captured image, as returned by get_imginfo()
        2. status : dict
            A dictionary containing the current status of the connected camera, as returned by get_status().
        """
        self._imagetype = imgtypename
        self.set_binning(binning = binning)
        log.info('[DARK] Start exposure (exptime = %.1f)'%exptime)
        self.device.StartExposure(Duration = exptime, Light = False)
        time.sleep(2*self._checktime)
        while not self.device.ImageReady:
            time.sleep(self._checktime)
        imginfo, status = self.get_imginfo()
        log.info(f'[{imgtypename.upper()}] Exposure finished (exptime = %.1f)'%exptime)
        self.status = self.get_status()
        return imginfo, status
    
    def abort(self):
        """
        Aborts the current exposure.
        """
        if self.device.CanAbortExposure:
            self.device.AbortExposure()
            log.warning('Camera aborted')
        self.status = self.get_status()
        
        
# %% Test
if __name__ == '__main__':
    C = Camera('127.0.0.1:32323',0)
    A = mainCamera(C)
    A.connect()
    A.cooler_on(5)
    light, status_1 = A.take_light(30)
    dark, status_2 = A.take_dark(3)
    bias, status_3 = A.take_bias(3)
    A.cooler_off(warmuptime=10)
    A.disconnect()

# %%
