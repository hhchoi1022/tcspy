
#%%
import numpy as np

from alpaca.camera import Camera
import alpaca

from devicecamera import deviceCamera
from saveimage import saveImage
from tcspy.configuration import mainConfig
from tcspy.utils import mainLogger
#%%
log = mainLogger(__name__).log()
class mainCamera(deviceCamera, saveImage, mainConfig):
    
    def __init__(self):
        mainConfig.__init__(self)
        deviceaddress = self.config['CAMERA_HOSTIP']+':'+self.config['CAMERA_PORTNUM']
        C = Camera(deviceaddress, int(self.config['CAMERA_DEVICENUM']))
        deviceCamera.__init__(self, device = C)
        try:
            self.connect()
        except:
            logtxt = 'Connection to the camera Failed'
            log.warning(logtxt)
            raise ConnectionError(logtxt)
    
    def write_img(self,
                  filename : 'str',
                  data : np.array,
                  info : alpaca.camera.Camera.ImageArrayInfo,
                  ):
        saveImage.__init__(self, imgdata = data, imginfo = info)
        self.writefile(filename = filename)
    
# %% Test
if __name__ == '__main__':
    CAM = mainCamera()
    CAM.cooleron(settemperature = float(CAM.config['CAMERA_SETTEMP']))
    for i in range(9):
        data, info = CAM.take_bias(binning = 1)
        CAM.write_img("Bias_00%d.fits"%(i+1), data = data, info = info)
    for i in range(9):
        pass
        #data, info = cam.take_dark(binning = 2, exptime = 5)
        #cam.write_img("Dark_00%d.fits"%i+1, data = data, info = info)
    for i in range(9):
        data, info = CAM.take_light(binning = 1, exptime = 5)
        CAM.write_img("Target_00%d.fits"%(i+1), data = data, info = info)


#%%