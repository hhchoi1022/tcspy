#%%
from astropy.time import Time
from astropy.io import fits
import numpy as np
from typing import Optional
from astropy.visualization import ImageNormalize
from astropy.visualization import ZScaleInterval, MinMaxInterval
from astropy.visualization import LinearStretch, LogStretch
import matplotlib.pyplot as plt 


from tcspy.configuration import mainConfig
from tcspy.devices.camera import mainCamera
from tcspy.devices.telescope import mainTelescope_pwi4
from tcspy.devices.filterwheel import mainFilterwheel
from tcspy.devices.observer import mainObserver


#%%
class mainImage(mainConfig):
    
    def __init__(self,
                 unitnum : int,
                 image_info : dict,
                 camera_info : dict,
                 telescope_info : dict,
                 filterwheel_info : dict,
                 focuser_info : dict,
                 observer_info : dict,
                 target_info : dict,
                 **kwargs
                 ):
        
        super().__init__(unitnum = unitnum)
        self._imginfo = image_info
        self._caminfo = camera_info
        self._telinfo = telescope_info
        self._filtinfo = filterwheel_info
        self._focusinfo = focuser_info
        self._obsinfo = observer_info
        self._targetinfo = target_info
        self.status = self._set_status()
        
    def show(self):
        figsize_x = 4 * self.header['NAXIS1']/4096
        figsize_y = 4 * self.header['NAXIS2']/4096
        norm = ImageNormalize(self.data, interval=ZScaleInterval(), stretch=LinearStretch())
        plt.figure(dpi = 300, figsize = (figsize_x, figsize_y))
        plt.imshow(self.data, cmap=plt.cm.gray, norm=norm, interpolation='none')
        plt.colorbar()
        
    def _set_status(self):
        status = dict()
        status['image'] = self._imginfo
        status['camera'] = self._caminfo
        status['telescope'] = self._telinfo
        status['filterwheel'] = self._filtinfo
        status['focuser'] = self._focusinfo
        status['observer'] = self._obsinfo
        status['target'] = self._targetinfo
        return status
    
    def _format_header(self,
                       value,
                       note : str = ''):
        return dict(value = value, note=  note)
        
    def _get_info_config(self):
        info = dict()
        # telescope
        info['TEL_IP'] = self._format_header(self.config['TELESCOPE_HOSTIP'],'Hosting IP for ALPACA telescope device')
        info['TEL_PRT'] =self._format_header(self.config['TELESCOPE_PORTNUM'],'Port number of ALPACA telescope device')
        info['TEL_NUM'] = self._format_header(self.config['TELESCOPE_DEVICENUM'],'Device number of ALPACA telescope device')
        info['FOCALLEN'] = self._format_header(self.config['TELESCOPE_FOCALLENGTH'],'Focal length of the telescope in mm')
        info['APTDIA'] = self._format_header(self.config['TELESCOPE_DIAMETER'], 'Diameter of the telescope in m')
        info['APTAREA'] = self._format_header(1e4*np.pi*(float(self.config['TELESCOPE_DIAMETER'])/2)**2, 'Aperture area of the telescope in mm^2')
        info['TEL_UNIT'] = self._format_header(self.unitnum, 'Telescope Unit number')  ############################################
        # camera
        info['CAM_IP'] = self._format_header(self.config['CAMERA_HOSTIP'],'Hosting IP for ALPACA camera device')
        info['CAM_PRT'] = self._format_header(self.config['CAMERA_PORTNUM'],'Port number of ALPACA camera device')
        info['CAM_NUM'] = self._format_header(self.config['CAMERA_DEVICENUM'],'Device number of ALPACA camera device')
        info['XPIXSZ'] = self._format_header(self.config['CAMERA_PIXSIZE'], 'Pixel width in microns')
        info['YPIXSZ'] = self._format_header(self.config['CAMERA_PIXSIZE'], 'Pixel height in microns')
        # filterwheel 
        info['FILT_IP'] = self._format_header(self.config['FTWHEEL_HOSTIP'],'Hosting IP for ALPACA filterwheel device')
        info['FILT_PRT'] = self._format_header(self.config['FTWHEEL_PORTNUM'],'Port number of ALPACA filterwheel device')
        info['FILT_NUM'] = self._format_header(self.config['FTWHEEL_DEVICENUM'],'Device number of ALPACA filterwheel device')
        # focuser
        info['FOC_IP'] = self._format_header(self.config['FOCUSER_HOSTIP'],'Hosting IP for ALPACA focuser device')
        info['FOC_PRT'] = self._format_header(self.config['FOCUSER_PORTNUM'],'Port number of ALPACA focuser device')
        info['FOC_NUM'] = self._format_header(self.config['FOCUSER_DEVICENUM'],'Device number of ALPACA focuser device')
        # focuser
        info['FOC_IP'] = self._format_header(self.config['WEATHER_HOSTIP'],'Hosting IP for ALPACA weather device')
        info['FOC_PRT'] = self._format_header(self.config['WEATHER_PORTNUM'],'Port number of ALPACA weather device')
        info['FOC_NUM'] = self._format_header(self.config['WEATHER_DEVICENUM'],'Device number of ALPACA weather device')
        # focuser
        info['FOC_IP'] = self._format_header(self.config['SAFEMONITOR_HOSTIP'],'Hosting IP for ALPACA weather device')
        info['FOC_PRT'] = self._format_header(self.config['SAFEMONITOR_PORTNUM'],'Port number of ALPACA weather device')
        info['FOC_NUM'] = self._format_header(self.config['SAFEMONITOR_DEVICENUM'],'Device number of ALPACA weather device')
        # logger
        info['LOGFILE'] = self._format_header(self.config['LOGGER_FILEPATH'], 'Log file path')
        return info
        
    def _get_info_camera(self):
        cam_info = self.status['camera']
        info = dict()
        info['INSTRUME'] = self._format_header(cam_info['name_cam'], 'Detector instrument name')
        info['EGAIN'] = self._format_header(cam_info['gain'], 'Eletrconic gain in e-/ADU')
        info['CCD-TEMP'] = self._format_header(cam_info['ccdtemp'], 'CCD temperature')
        info['COL-POWE'] = self._format_header(cam_info['power_cooler'], 'CCD cooler power (100 for maximum)')
        return info
    
    def _get_info_telescope(self):
        tel_info = self.status['telescope']
        info = dict()
        info['ALTITUDE'] = self._format_header(tel_info['alt'], 'Altitude of the telescope pointing')
        info['AZIMUTH'] = self._format_header(tel_info['az'], 'Azimuth of the telescope pointing')
        info['RA'] = self._format_header(tel_info['ra'], 'Right ascension of the telescope pointing')
        info['DEC'] = self._format_header(tel_info['dec'], 'Declination of the telescope pointing')
        return info
        
    def _get_info_filterwheel(self):
        filt_info = self.status['filterwheel']
        info = dict()
        info['FILTER'] = self._format_header(filt_info['filter'], 'Name of the filter')
        return info

    def _get_info_focuser(self):
        focus_info = self.status['focuser']
        info = dict()
        info['FOCUSPOS'] = self._format_header(focus_info['position'], 'Position of the focuser') #### Customized
        return info
    
    def _get_info_observer(self):
        obs_info = self.status['observer']
        info = dict()
        info['TELESCOP'] = self._format_header(obs_info['name_observatory'], 'Name of the telescope')
        info['OBSERVER'] = self._format_header(obs_info['name_observer'], 'Name of the observer') 
        info['SITELAT'] = self._format_header(obs_info['latitude'], 'Latitude of the observatory') 
        info['SITELONG'] = self._format_header(obs_info['longitude'], 'Longitude of the observatory') 
        info['SITEELEV'] = self._format_header(obs_info['elevation'], 'Elevation of the observatory')  #### Customized
        return info
    
    def _get_info_image(self):
        img_info = self.status['image']
        info = dict()
        #info['NAXIS1'] = self._format_header(img_info['numX'], '') 
        #info['NAXIS2'] = self._format_header(img_info['numY'], '') 
        info['IMAGETYP'] = self._format_header(img_info['imgtype'], 'Type of the image')
        info['EXPTIME'] = self._format_header(img_info['exptime'], 'Duration of exposure time [sec]')
        info['DATE-OBS'] = self._format_header(img_info['date_obs'], 'Date of the observation [ISO format]')
        info['JD'] = self._format_header(img_info['jd'], 'Julian date')
        ##### MJD
        info['XBINNING'] = self._format_header(img_info['binningX'], 'Binning level along the X-axis')
        info['YBINNING'] = self._format_header(img_info['binningY'], 'Binning level along the Y-axis')
        return info
    
    def _get_info_target(self):
        tar_info = self.status['target']
        info = dict()
        info['OBJECT'] = self._format_header(tar_info['name'], 'Name of the target')
        info['OBJCTRA'] = self._format_header(tar_info['ra'], 'Right ascension of the target')
        info['OBJCTDEC'] = self._format_header(tar_info['dec'], 'Declination of the target')
        info['OBJCTALT'] = self._format_header(tar_info['alt'], 'Altitude of the target')
        info['OBJCTAZ'] = self._format_header(tar_info['az'], 'Azimuth of the target')
        info['OBJCTHA'] = self._format_header(tar_info['hourangle'], 'Hourangle of the target')
        return info
    
    @property
    def hdu(self):
        tel_info = self._get_info_telescope()
        cam_info = self._get_info_camera()
        focus_info = self._get_info_focuser()
        filt_info = self._get_info_filterwheel()
        img_info = self._get_info_image()
        tar_info = self._get_info_target()
        config_info = self._get_info_config()
        obs_info = self._get_info_observer()
        all_info = {**tel_info,**cam_info,**focus_info,**filt_info,**img_info,**tar_info,**config_info,**obs_info}
        hdu = fits.PrimaryHDU()
        hdu.data = self._imginfo['data']
        for key, value in all_info.items():
            hdu.header[key] = (value['value'],str(value['note']))
        return hdu
    
    @property
    def header(self):
        return self.hdu.header
    
    @property
    def data(self):
        return self.hdu.data
    
    def save(self, filename):
        self.hdu.writeto(self.config['IMAGE_FILEPATH']+filename, overwrite = True) ########## Raw file naming convention
    

            
            

# %%
