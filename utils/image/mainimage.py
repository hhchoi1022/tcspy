#%%
from astropy.time import Time
from astropy.io import fits
import numpy as np
from typing import Optional
from astropy.visualization import ImageNormalize
from astropy.visualization import ZScaleInterval
from astropy.visualization import LinearStretch
import matplotlib.pyplot as plt 
import os
import re
from tcspy.configuration import mainConfig
from datetime import datetime
#%%
class mainImage(mainConfig):
    
    def __init__(self,
                 frame_number : int,
                 config_info : dict,
                 image_info : dict,
                 camera_info : dict = None,
                 telescope_info : dict = None,
                 filterwheel_info : dict = None,
                 focuser_info : dict = None,
                 observer_info : dict = None,
                 target_info : dict = None,
                 weather_info : dict = None
                 ):
        
        self._framenum = frame_number
        self._configinfo = config_info
        self._imginfo = image_info
        self._caminfo = camera_info
        self._telinfo = telescope_info
        self._filtinfo = filterwheel_info
        self._focusinfo = focuser_info
        self._obsinfo = observer_info
        self._targetinfo = target_info
        self._weatherinfo = weather_info
        
    def show(self):
        figsize_x = 4 * self.header['NAXIS1']/4096
        figsize_y = 4 * self.header['NAXIS2']/4096
        norm = ImageNormalize(self.data, interval=ZScaleInterval(), stretch=LinearStretch())
        plt.figure(dpi = 300, figsize = (figsize_x, figsize_y))
        plt.imshow(self.data, cmap=plt.cm.gray, norm=norm, interpolation='none')
        plt.colorbar()
        
    
    def _format_filename(self):
        format_filename = self._configinfo['FILENAME_FORMAT']
        key_data = self.header
        
        key_data['FRAMENUM'] = '%.4d' %(self._framenum)
        
        dt_ut = datetime.strptime(key_data['DATE-OBS'], '%Y-%m-%dT%H:%M:%S.%f')
        dt_lt = datetime.strptime(key_data['DATE-LOC'], '%Y-%m-%d %H:%M:%S.%f')
        key_data['UTCDATE'] = '%.4d%.2d%.2d' % (dt_ut.year, dt_ut.month, dt_ut.day)
        key_data['LTCDATE'] = '%.4d%.2d%.2d' % (dt_lt.year, dt_lt.month, dt_lt.day)
        key_data['UTCTIME'] = '%.2d%.2d%.2d' % (dt_ut.hour, dt_ut.minute, dt_ut.second)
        key_data['LTCTIME'] = '%.2d%.2d%.2d' % (dt_lt.hour, dt_lt.minute, dt_lt.second)
        
        key_data['UTCDATE_'] = '%.4d_%.2d_%.2d' % (dt_ut.year, dt_ut.month, dt_ut.day)
        key_data['LTCDATE_'] = '%.4d_%.2d_%.2d' % (dt_lt.year, dt_lt.month, dt_lt.day)
        key_data['UTCTIME_'] = '%.2d_%.2d_%.2d' % (dt_ut.hour, dt_ut.minute, dt_ut.second)
        key_data['LTCTIME_'] = '%.2d_%.2d_%.2d' % (dt_lt.hour, dt_lt.minute, dt_lt.second)
        
        key_data['UTCDATE-'] = '%.4d-%.2d-%.2d' % (dt_ut.year, dt_ut.month, dt_ut.day)
        key_data['LTCDATE-'] = '%.4d-%.2d-%.2d' % (dt_lt.year, dt_lt.month, dt_lt.day)
        key_data['UTCTIME-'] = '%.2d-%.2d-%.2d' % (dt_ut.hour, dt_ut.minute, dt_ut.second)
        key_data['LTCTIME-'] = '%.2d-%.2d-%.2d' % (dt_lt.hour, dt_lt.minute, dt_lt.second)
        
        key_dict = dict()
        for key in key_data.keys():
            key_dict[key] = str(key_data[key])
            
        
        def replace_placeholder(match):
            key = match.group(1)
            return key_dict.get(key, match.group(0))

        # Use regular expressions to find and replace the placeholders
        pattern = r'\$\$(.*?)\$\$'
        output_string = re.sub(pattern, replace_placeholder, format_filename)
        return output_string
    
    def _format_header(self,
                       value,
                       note : str = ''):
        return dict(value = value, note=  note)
        
    def _add_configinfo_to_hdr(self):
        
        info = dict()
        # telescope
        info['TEL_IP'] = self._format_header(self._configinfo['TELESCOPE_HOSTIP'],'Hosting IP for ALPACA telescope device')
        info['TEL_PRT'] =self._format_header(self._configinfo['TELESCOPE_PORTNUM'],'Port number of ALPACA telescope device')
        info['TEL_NUM'] = self._format_header(self._configinfo['TELESCOPE_DEVICENUM'],'Device number of ALPACA telescope device')
        info['FOCALLEN'] = self._format_header(self._configinfo['TELESCOPE_FOCALLENGTH'],'Focal length of the telescope in mm')
        info['APTDIA'] = self._format_header(self._configinfo['TELESCOPE_DIAMETER'], 'Diameter of the telescope in m')
        info['APTAREA'] = self._format_header(1e4*np.pi*(float(self._configinfo['TELESCOPE_DIAMETER'])/2)**2, 'Aperture area of the telescope in mm^2')
        # camera
        info['CAM_IP'] = self._format_header(self._configinfo['CAMERA_HOSTIP'],'Hosting IP for ALPACA camera device')
        info['CAM_PRT'] = self._format_header(self._configinfo['CAMERA_PORTNUM'],'Port number of ALPACA camera device')
        info['CAM_NUM'] = self._format_header(self._configinfo['CAMERA_DEVICENUM'],'Device number of ALPACA camera device')
        info['XPIXSZ'] = self._format_header(self._configinfo['CAMERA_PIXSIZE'], 'Pixel width in microns')
        info['YPIXSZ'] = self._format_header(self._configinfo['CAMERA_PIXSIZE'], 'Pixel height in microns')
        # filterwheel 
        info['FILT_IP'] = self._format_header(self._configinfo['FTWHEEL_HOSTIP'],'Hosting IP for ALPACA filterwheel device')
        info['FILT_PRT'] = self._format_header(self._configinfo['FTWHEEL_PORTNUM'],'Port number of ALPACA filterwheel device')
        info['FILT_NUM'] = self._format_header(self._configinfo['FTWHEEL_DEVICENUM'],'Device number of ALPACA filterwheel device')
        # focuser
        info['FOC_IP'] = self._format_header(self._configinfo['FOCUSER_HOSTIP'],'Hosting IP for ALPACA focuser device')
        info['FOC_PRT'] = self._format_header(self._configinfo['FOCUSER_PORTNUM'],'Port number of ALPACA focuser device')
        info['FOC_NUM'] = self._format_header(self._configinfo['FOCUSER_DEVICENUM'],'Device number of ALPACA focuser device')
        # focuser
        info['FOC_IP'] = self._format_header(self._configinfo['WEATHER_HOSTIP'],'Hosting IP for ALPACA weather device')
        info['FOC_PRT'] = self._format_header(self._configinfo['WEATHER_PORTNUM'],'Port number of ALPACA weather device')
        info['FOC_NUM'] = self._format_header(self._configinfo['WEATHER_DEVICENUM'],'Device number of ALPACA weather device')
        # focuser
        info['FOC_IP'] = self._format_header(self._configinfo['SAFEMONITOR_HOSTIP'],'Hosting IP for ALPACA weather device')
        info['FOC_PRT'] = self._format_header(self._configinfo['SAFEMONITOR_PORTNUM'],'Port number of ALPACA weather device')
        info['FOC_NUM'] = self._format_header(self._configinfo['SAFEMONITOR_DEVICENUM'],'Device number of ALPACA weather device')
        # logger
        info['LOGFILE'] = self._format_header(self._configinfo['LOGGER_PATH'], 'Log file path')
        return info
    
    def _add_weatinfo_to_hdr(self):
        info = dict()
        info['DATE-WEA'] = None
        info['TEMP'] = None
        info['HUMIDITY'] = None
        info['PRESSURE'] = None
        info['DEWPOINT'] = None
        info['WINDSPED'] = None
        info['WINDGUST'] = None
        info['DEWPOINT'] = None
        info['SKYBRIGT'] = None
        info['SKYTEMP'] = None
        info['SKYFWHM'] = None
        info['CLUDFRAC'] = None
        info['RAINRATE'] = None

        if self._weatherinfo:
            info['DATE-WEA'] = self._format_header(self._weatherinfo['update_time'], 'UTC of the latest weather update')
            info['TEMP'] = self._format_header(self._weatherinfo['temperature'], 'Atmospheric temperature (deg C) at the observatory')
            info['HUMIDITY'] = self._format_header(self._weatherinfo['humidity'], 'Atmospheric relative humidity (0-100%) at the observatory')
            info['PRESSURE'] = self._format_header(self._weatherinfo['pressure'], 'Atmospheric pressure (hPa) at the observatory altitude')
            info['DEWPOINT'] = self._format_header(self._weatherinfo['dewpoint'], 'Atmospheric dew point temperature (deg C) at the observatory')
            info['WINDSPED'] = self._format_header(self._weatherinfo['windspeed'], 'Wind speed (m/s) at the observatory')
            info['WINDGUST'] = self._format_header(self._weatherinfo['windgust'], 'Peak 3 second wind gust (m/s) at the observatory over the last 2 minutes')
            info['DEWPOINT'] = self._format_header(self._weatherinfo['winddirection'], 'Direction (deg) from which the wind is blowing at the observatory')
            info['SKYBRIGT'] = self._format_header(self._weatherinfo['skybrightness'], 'Sky quality (mag per sq-arcsec) at the observatory')
            info['SKYTEMP'] = self._format_header(self._weatherinfo['skytemperature'], 'Sky temperature (deg C) at the observatory')
            info['SKYFWHM'] = self._format_header(self._weatherinfo['fwhm'], 'Seeing (FWHM in arc-sec) at the observatory')
            info['CLUDFRAC'] = self._format_header(self._weatherinfo['cloudfraction'], 'Amount of sky obscured by cloud (0.0-1.0)')
            info['RAINRATE'] = self._format_header(self._weatherinfo['rainrate'], 'Rain rate (mm/hr) at the observatory')
        return info
    
    def _add_caminfo_to_hdr(self):
        info = dict()
        info['INSTRUME'] = None
        info['EGAIN'] = None
        info['CCD-TEMP'] = None
        info['COL-POWE'] = None
        if self._caminfo:
            info['INSTRUME'] = self._format_header(self._caminfo['name_cam'], 'Detector instrument name')
            info['GAIN'] = self._format_header(self._caminfo['gain'], 'Gain from the camera configuration')
            info['EGAIN'] = self._format_header(self._caminfo['egain'], 'Eletrconic gain in e-/ADU')
            info['CCD-TEMP'] = self._format_header(self._caminfo['ccdtemp'], 'CCD temperature')
            info['COL-POWE'] = self._format_header(self._caminfo['power_cooler'], 'CCD cooler power (100 for maximum)')
        return info
    
    def _add_telinfo_to_hdr(self):
        info = dict()
        info['ALTITUDE'] = None
        info['AZIMUTH'] = None
        info['RA'] = None
        info['DEC'] = None
        if self._telinfo:
            info['ALTITUDE'] = self._format_header(self._telinfo['alt'], 'Altitude of the telescope pointing')
            info['AZIMUTH'] = self._format_header(self._telinfo['az'], 'Azimuth of the telescope pointing')
            info['RA'] = self._format_header(self._telinfo['ra'], 'Right ascension of the telescope pointing')
            info['DEC'] = self._format_header(self._telinfo['dec'], 'Declination of the telescope pointing')
        return info
        
    def _add_filtwheelinfo_to_hdr(self):
        info = dict()
        info['FILTER'] = None
        if self._filtinfo:
            info['FILTER'] = self._format_header(self._filtinfo['filter'], 'Name of the filter')
        return info

    def _add_focusinfo_to_hdr(self):
        info = dict()
        info['FOCUSPOS'] = None
        if self._focusinfo:
            info['FOCUSPOS'] = self._format_header(self._focusinfo['position'], 'Position of the focuser') #### Customized
        return info
    
    def _add_obsinfo_to_hdr(self):
        info = dict()
        info['TELESCOP'] = None
        info['OBSERVER'] = None
        info['SITELAT'] = None
        info['SITELONG'] = None
        info['SITEELEV'] = None
        if self._obsinfo:
            info['TELESCOP'] = self._format_header(self._obsinfo['name_observatory'], 'Name of the telescope')
            info['OBSERVER'] = self._format_header(self._obsinfo['name_observer'], 'Name of the observer') 
            info['SITELAT'] = self._format_header(self._obsinfo['latitude'], 'Latitude of the observatory') 
            info['SITELONG'] = self._format_header(self._obsinfo['longitude'], 'Longitude of the observatory') 
            info['SITEELEV'] = self._format_header(self._obsinfo['elevation'], 'Elevation of the observatory')
        return info
    
    def _add_imginfo_to_hdr(self):
        info = dict()
        info['IMAGETYP'] = self._format_header(self._imginfo['imgtype'], 'Type of the image')
        info['EXPTIME'] = self._format_header(self._imginfo['exptime'], 'Duration of exposure time [sec]')
        info['DATE-OBS'] = self._format_header(self._imginfo['date_obs_utc'], '[UTC] Date of the observation')
        info['DATE-LOC'] = self._format_header(self._imginfo['date_obs_ltc'], '[Local] Date of the observation')
        info['JD'] = self._format_header(self._imginfo['jd'], 'Julian date')
        ##### MJD
        info['XBINNING'] = self._format_header(self._imginfo['binningX'], 'Binning level along the X-axis')
        info['YBINNING'] = self._format_header(self._imginfo['binningY'], 'Binning level along the Y-axis')
        return info
    
    def _add_targetinfo_to_hdr(self):
        info = dict()
        info['OBJECT'] = None
        info['OBJCTRA'] = None
        info['OBJCTDEC'] = None
        info['OBJCTALT'] = None
        info['OBJCTAZ'] = None
        info['OBJCTHA'] = None
        if self._targetinfo:
            info['OBJECT'] = self._format_header(self._targetinfo['name'], 'Name of the target')            
            info['OBJTYPE'] = self._format_header(self._targetinfo['objtype'], 'Type of the target')
            info['OBJCTRA'] = self._format_header(self._targetinfo['ra'], 'Right ascension of the target')
            info['OBJCTDEC'] = self._format_header(self._targetinfo['dec'], 'Declination of the target')
            info['OBJCTALT'] = self._format_header(self._targetinfo['alt'], 'Altitude of the target')
            info['OBJCTAZ'] = self._format_header(self._targetinfo['az'], 'Azimuth of the target')
            info['OBJCTHA'] = self._format_header(self._targetinfo['hourangle'], 'Hourangle of the target')
            info['OBSMODE'] = self._format_header(self._targetinfo['obsmode'], 'Mode of the observation')
        return info
    
    @property
    def hdu(self):
        telinfo = self._add_telinfo_to_hdr()
        caminfo = self._add_caminfo_to_hdr()
        focusinfo = self._add_focusinfo_to_hdr()
        filtinfo = self._add_filtwheelinfo_to_hdr()
        imginfo = self._add_imginfo_to_hdr()
        targetinfo = self._add_targetinfo_to_hdr()
        configinfo = self._add_configinfo_to_hdr()
        obsinfo = self._add_obsinfo_to_hdr()
        weatherinfo = self._add_weatinfo_to_hdr()
        all_info = {**telinfo,**caminfo,**focusinfo,**filtinfo,**imginfo,**targetinfo,**configinfo,**obsinfo,**weatherinfo}
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
    
    def save(self):
        if not os.path.isdir(self._configinfo['IMAGE_PATH']):
            os.makedirs(self._configinfo['IMAGE_PATH'])
        filename = self._format_filename()
        filepath = self._configinfo['IMAGE_PATH']+filename
        if os.path.exists(filepath):
            filepath = self._configinfo['IMAGE_PATH']+"dup_"+filename
            self.hdu.writeto(filepath, overwrite = False) 
        else:
            self.hdu.writeto(filepath, overwrite = False) 
        return filepath

# %%
