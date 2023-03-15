#%%
import glob, os
from astropy.io import ascii
from astropy.table import Table
import json
#%%
class mainConfig:
    def __init__(self,
                 unitnum : int,
                 **kwargs):
        self.unitnum = unitnum
        configfilekey = os.path.dirname(__file__)+f'/unit{self.unitnum}'+'/*.config',
        self._configfiles = glob.glob(configfilekey[0])
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

    def _initialize_config(self,
                           savedir = f'{os.path.dirname(__file__)}'):
        savepath = savedir + f'/unit{self.unitnum}/'
        if not os.path.exists(savepath):
            os.makedirs(savepath, exist_ok= True)
        def make_configfile(dict_params, 
                            filename : str,
                            savepath = savepath):
            with open(savepath + filename, 'w') as f:
                json.dump(dict_params, f , indent = 4)
            print('New configuration file made : %s'%(savepath+filename))
        ###### ALL CONFIGURATION PARAMETERS(EDIT HERE!!!) ######
        observer_params = dict(OBSERVER_LONGITUDE = 127.97805, # Obstec = -70.7804,
                       OBSERVER_LATITUDE = 37.56583, # Obstec = -30.4704,
                       OBSERVER_ELEVATION = 140, # Obstec = 1580,
                       OBSERVER_TIMEZONE = 'Asia/Seoul', #'America/Santiago'
                       OBSERVER_NAME = 'Hyeonho Choi',
                       OBSERVER_OBSERVATORY = '7DT_%.2d'%self.unitnum
                       )
        weather_params = dict(WEATHER_HOSTIP = '192.168.0.%d'%self.unitnum,
                              WEATHER_PORTNUM = '11111',
                              WEATHER_DEVICENUM = 0,
                              WEATHER_CHECKTIME = 0.5,
                              WEATHER_CONSTRAINTSFILE = os.path.dirname(__file__)+'/WeatherConstraints.data')
        
        dome_params = dict(DOME_HOSTIP = '192.168.0.%d'%self.unitnum,
                           DOME_PORTNUM = '11111',
                           DOME_DEVICENUM = 0,
                           DOME_CHECKTIME = 0.5)
        safetymonitor_params = dict(SAFEMONITOR_HOSTIP = '192.168.0.%d'%self.unitnum,
                                    SAFEMONITOR_PORTNUM = '11111',
                                    SAFEMONITOR_DEVICENUM = 0,
                                    SAFEMONITOR_CHECKTIME = 0.5)
        
        telescope_params = dict(TELESCOPE_DEVICE = 'Alpaca', # Alpaca or PWI4
                                TELESCOPE_HOSTIP = '192.168.0.%d'%self.unitnum,
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
        camera_params = dict(CAMERA_HOSTIP = '192.168.0.%d'%self.unitnum,
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
        filterwheel_params = dict(FTWHEEL_HOSTIP = '192.168.0.%d'%self.unitnum,
                                  FTWHEEL_PORTNUM = '11111',
                                  FTWHEEL_DEVICENUM = 0,
                                  FTWHEEL_NAME = '',
                                  FTWHEEL_CHECKTIME = 0.5,
                                  FTWHEEL_OFFSETFILE = os.path.dirname(__file__)+'/FilterOffset.data')
        focuser_params = dict(FOCUSER_HOSTIP = '192.168.0.%d'%self.unitnum,
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
        path_params = dict(LOGGER_FILEPATH = f'/home/hhchoi1022/Desktop/log/unit{self.unitnum}/',
                           IMAGE_FILEPATH = f'/home/hhchoi1022/Desktop/images/unit{self.unitnum}/'
                           )
        # For more camera info : https://www.gxccd.com/art?id=647&lang=409
        logger_params = dict(LOGGER_SAVE = True,
                            LOGGER_LEVEL = 'INFO',
                            LOGGER_FORMAT = '[%(levelname)s]%(asctime)-15s | %(message)s',
                            )

        general_params = dict(TCSPY_VERSION = 'Version 1.0',
                            TCSPY_NAME = 'TCSpy'
                            )
        filt_offset = dict(w425 = -999,
                           g = -999,
                           r = -999,
                           i = -999
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
        os.makedirs(path_params['LOGGER_FILEPATH'], exist_ok= True)
        os.makedirs(path_params['IMAGE_FILEPATH'], exist_ok= True)

#%% Temporary running 
if __name__ == '__main__':
    A = mainConfig(unitnum = 5)
    A.initialize_config()

#%%
# %%
