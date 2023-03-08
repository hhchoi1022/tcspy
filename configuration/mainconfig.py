#%%
import glob, os
from astropy.io import ascii
from astropy.table import Table
import json
#%%
class mainConfig:
    def __init__(self,
                 configfilekey : str = os.path.dirname(__file__)+'/*.config',
                 **kwargs):
        self._configfiles = glob.glob(configfilekey)
        if len(self._configfiles) == 0:
            print('No configuration file is found.\nTo make default configuration files, run tcspy.configuration.make_config')
        else:
            pass
            self.config = self._load_configuration()
            
    def _load_configuration(self):
        all_config = dict()
        for configfile in self._configfiles:
            with open(configfile, 'r') as f:
                config = json.load(f)
                all_config.update(config)
        return all_config

    def _make_configuration(dict_params : dict,
                            savepath = f'{os.path.dirname(__file__)}/'):
        def make_configfile(dict_params, 
                            filename : str,
                            savepath = savepath):
            with open(savepath + filename, 'w') as f:
                json.dump(dict_params, f , indent = 4)
            print('New configuration file made : %s'%(savepath+filename))
        ###### ALL CONFIGURATION PARAMETERS(EDIT HERE!!!) ######
        observer_params = dict(OBSERVER_LONGITUDE = -70.7804,#127.97805, # Obstec = -70.7804,
                       OBSERVER_LATITUDE = -30.4704,#37.56583, # Obstec = -30.4704,
                       OBSERVER_ELEVATION = 1580,#140, # Obstec = 1580,
                       OBSERVER_TIMEZONE = 'America/Santiago',#'Asia/Seoul',
                       OBSERVER_NAME = 'Hyeonho Choi',
                       OBSERVER_OBSERVATORY = '7DT_01'
                       )
        weather_params = dict(WEATHER_HOSTIP = '192.168.0.4',
                              WEATHER_PORTNUM = '11111',
                              WEATHER_DEVICENUM = 0,
                              WEATHER_CHECKTIME = 0.5,
                              WEATHER_CONSTRAINTSFILE = os.path.dirname(__file__)+'/WeatherConstraints.data')
        
        dome_params = dict(DOME_HOSTIP = '192.168.0.4',
                           DOME_PORTNUM = '11111',
                           DOME_DEVICENUM = 0,
                           DOME_CHECKTIME = 0.5)
        safetymonitor_params = dict(SAFEMONITOR_HOSTIP = '192.168.0.4',
                                    SAFEMONITOR_PORTNUM = '11111',
                                    SAFEMONITOR_DEVICENUM = 0,
                                    SAFEMONITOR_CHECKTIME = 0.5)
        
        telescope_params = dict(TELESCOPE_DEVICE = 'Alpaca', # Alpaca or PWI4
                                TELESCOPE_HOSTIP = '192.168.0.4',
                                TELESCOPE_PORTNUM = '11111',
                                TELESCOPE_DEVICENUM = 0,
                                TELESCOPE_PARKALT = 0,
                                TELESCOPE_PARKAZ = 270,
                                TELESCOPE_RMSRA = 0.15,
                                TELESCOPE_RMSDEC = 0.15,
                                TELESCOPE_CHECKTIME = 0.5,
                                TELESCOPE_DIAMETER = 0.5,
                                TELESCOPE_APAREA = 0.196,
                                TELESCOPE_FOCALLENGTH = 1500
                                )
        camera_params = dict(CAMERA_HOSTIP = '192.168.0.4',
                            CAMERA_PORTNUM = '11111',
                            CAMERA_DEVICENUM = 0,
                            CAMERA_NAME = 'Moravian C3-61000',
                            CAMERA_CCDNAME = 'IMX455',
                            CAMERA_RESOLUTION_X = 1920,
                            CAMERA_RESOLUTION_Y = 1200,
                            CAMERA_PIXSIZE = 3.76, # micron
                            CAMERA_GAIN = 1,
                            CAMERA_READNOISE = 3.51,
                            CAMERA_FULLCAP = 52800,
                            CAMERA_E_to_ADU = 0.8, # e-/ADU
                            CAMERA_DARKNOISE = 0.1,                     
                            CAMERA_MINEXPOSURE = 19.5, # microseconds
                            CAMERA_CHECKTIME = 0.5
                            )
        filterwheel_params = dict(FTWHEEL_HOSTIP = '192.168.0.4',
                                  FTWHEEL_PORTNUM = '11111',
                                  FTWHEEL_DEVICENUM = 0,
                                  FTWHEEL_NAME = '',
                                  FTWHEEL_CHECKTIME = 0.5,
                                  FTWHEEL_OFFSETFILE = os.path.dirname(__file__)+'/FilterOffset.data')
        focuser_params = dict(FOCUSER_HOSTIP = '192.168.0.4',
                              FOCUSER_PORTNUM = '11111',
                              FOCUSER_DEVICENUM = 0,
                              FOCUSER_NAME = '',
                              FOCUSER_CHECKTIME = 0.5,
                              FOCUSER_HALTTOL = 10000,
                              FOCUSER_WARNTOL = 5000)
        target_params = dict(TARGET_MINALT = -10,
                             TARGET_MAXALT = 90,
                             TARGET_MAX_SUNALT = None,
                             TARGET_MOONSEP = 40,
                             TARGET_MAXAIRMASS = None
                             )
        path_params = dict(LOGGER_FILEPATH = '/Users/hhchoi1022/Desktop/TCSpy/log/',
                           IMAGE_FILEPATH = '/Users/hhchoi1022/Desktop/TCSpy/images/'
                           )
        # For more camera info : https://www.gxccd.com/art?id=647&lang=409
        logger_params = dict(LOGGER_SAVE = False,
                            LOGGER_LEVEL = 'INFO',
                            LOGGER_FORMAT = '[%(levelname)s]%(asctime)-15s | %(message)s',
                            )

        general_params = dict(TCSPY_VERSION = 'Version 1.0',
                            TCSPY_NAME = 'TCSpy'
                            )
        filt_offset = dict(w400 = -999,
                           w425 = -999,
                           w450 = -999,
                           w475 = -999,
                           w500 = -999,
                           w525 = -999,
                           w550 = -999,
                           w575 = -999
                           )
        
        weather_constraints = dict(HUMIDITY = 85,
                                   RAINRATE = 1,
                                   SKYMAG = 10,
                                   TEMPERATURE_UPPER = 40,
                                   TEMPERATURE_LOWER = -25,
                                   WINDSPEED = 20)
        
        make_configfile(observer_params, filename = 'Observer.config')
        make_configfile(telescope_params, filename = 'Telescope.config')
        make_configfile(camera_params, filename = 'Camera.config')
        make_configfile(logger_params, filename = 'Logger.config')
        make_configfile(general_params, filename = 'General.config')
        make_configfile(path_params, filename = 'Path.config')
        make_configfile(filterwheel_params, filename = 'FilterWheel.config')
        make_configfile(focuser_params, filename = 'Focuser.config')
        make_configfile(target_params, filename = 'Target.config')
        make_configfile(weather_params, filename = 'Weather.config')
        make_configfile(dome_params, filename = 'Dome.config')
        make_configfile(safetymonitor_params, filename = 'SafetyMonitor.config')
        make_configfile(filt_offset, filename = 'FilterOffset.data')
        make_configfile(weather_constraints, filename = 'WeatherConstraints.data')


#%% Temporary running 
if __name__ == '__main__':
    A = mainConfig()
    A._make_configuration()

#%%
# %%
