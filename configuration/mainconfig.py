# Written by Hyeonho Choi 2023.01
# %%
import glob
import os
from astropy.io import ascii
import json

class mainConfig:
    def __init__(self,
                 unitnum: int = None,
                 configpath : str = '/home/hhchoi1022/tcspy/configuration/',
                 **kwargs):
        self.unitnum = unitnum
        self.config = dict()
        
        if self.unitnum:
            # Specified units config params
            self._configfilepath_unit = configpath + '7DT%.2d' % self.unitnum + '/'
            self._configfilekey_unit = self._configfilepath_unit + '*.config'
            self._configfiles_unit = glob.glob(self._configfilekey_unit)
            if len(self._configfiles_unit) == 0:
                print('No configuration file is found.\nTo make default configuration files, run tcspy.configuration.make_config')
            else:
                config_unit = self._load_configuration(self._configfiles_unit)
                self.config.update(config_unit)
                
        # global config params
        self._configfilepath_global = configpath
        self._configfilekey_global = self._configfilepath_global + '*.config'
        self._configfiles_global = glob.glob(self._configfilekey_global)
            
        if len(self._configfiles_global) == 0:
            print('No configuration file is found.\nTo make default configuration files, run tcspy.configuration.make_config')
        else:
            config_global = self._load_configuration(self._configfiles_global)
            self.config.update(config_global)

    def _load_configuration(self, 
                            configfiles):
        all_config = dict()
        for configfile in configfiles:
            with open(configfile, 'r') as f:
                config = json.load(f)
                all_config.update(config)
        return all_config

    def _initialize_config(self,
                           ip_address: str = '10.0.106.6',
                           portnum : int = '11111'):
        savepath_unit = self._configfilepath_unit
        if not os.path.exists(savepath_unit):
            os.makedirs(savepath_unit, exist_ok=True)

        def make_configfile(dict_params,
                            filename: str,
                            savepath=savepath_unit):
            with open(savepath + filename, 'w') as f:
                json.dump(dict_params, f, indent=4)
            print('New configuration file made : %s' % (savepath+filename))
            
        ###### ALL CONFIGURATION PARAMETERS(EDIT HERE!!!) #####
        telescope_params = dict(TELESCOPE_DEVICETYPE='PWI4',  # Alpaca or PWI4
                                TELESCOPE_HOSTIP= ip_address,
                                TELESCOPE_PORTNUM='8220',
                                TELESCOPE_DEVICENUM=0,
                                TELESCOPE_PARKALT=40,
                                TELESCOPE_PARKAZ=300,
                                TELESCOPE_RMSRA=0.15,
                                TELESCOPE_RMSDEC=0.15,
                                TELESCOPE_CHECKTIME=0.5,
                                TELESCOPE_DIAMETER=0.5,
                                TELESCOPE_APAREA=0.196,
                                TELESCOPE_FOCALLENGTH=1500,
                                TELESCOPE_SETTLETIME=3, #seconds
                                )
        camera_params = dict(CAMERA_HOSTIP= ip_address,
                             CAMERA_PORTNUM=portnum,
                             CAMERA_DEVICENUM=0,
                             CAMERA_PIXSIZE=3.76,  # micron
                             CAMERA_CHECKTIME=0.5)
                             
        filterwheel_params = dict(FTWHEEL_HOSTIP= ip_address,
                                  FTWHEEL_PORTNUM=portnum,
                                  FTWHEEL_DEVICENUM=0,
                                  FTWHEEL_CHECKTIME=0.5,
                                  FTWHEEL_OFFSETFILE =f"{savepath_unit}filter.offset")

        focuser_params = dict(FOCUSER_DEVICETYPE='PWI4',  # Alpaca or PWI4
                              FOCUSER_HOSTIP= ip_address,
                              FOCUSER_PORTNUM='8220',
                              FOCUSER_DEVICENUM=0,
                              FOCUSER_MINSTEP= 2000,
                              FOCUSER_MAXSTEP= 14000,
                              FOCUSER_CHECKTIME=0.5)
        
        observer_params = dict(OBSERVER_LONGITUDE= -70.7804,
                               OBSERVER_LATITUDE= -30.4704,
                               OBSERVER_ELEVATION= 1580,
                               OBSERVER_TIMEZONE= 'America/Santiago',
                               OBSERVER_NAME='Hyeonho Choi',
                               OBSERVER_OBSERVATORY='7DT%.2d' % self.unitnum
                               )
        
        image_params = dict(FILENAME_FORMAT= "$$TELESCOP$$-$$UTCDATE$$-$$UTCTIME$$-$$OBJECT$$-$$FILTER$$-$$EXPTIME$$s-$$FRAMENUM$$.fits",
                            IMAGE_PATH=f'/data1/obsdata/7DT%.2d/images/'%(self.unitnum))
        
        logger_params = dict(LOGGER_SAVE=True,
                             LOGGER_LEVEL='INFO', 
                             LOGGER_FORMAT='[%(levelname)s]%(asctime)-15s | %(message)s',
                             LOGGER_PATH= f'/data1/obsdata/7DT%.2d/log/'%(self.unitnum))
        
        # Share configuration
        

        weather_params = dict(WEATHER_HOSTIP= '10.0.11.3',#ip_address, #'10.0.11.3'
                              WEATHER_PORTNUM= 5575,#portnum, #5575
                              WEATHER_DEVICENUM=0,
                              WEATHER_CHECKTIME=0.5,
                              WEATHER_HUMIDITY=85,
                              WEATHER_RAINRATE=80,
                              WEATHER_SKYMAG=10,
                              WEATHER_TEMPERATURE_UPPER=-25,
                              WEATHER_TEMPERATURE_LOWER=40,
                              WEATHER_WINDSPEED=20)

        dome_params = dict(DOME_HOSTIP= ip_address,
                           DOME_PORTNUM=portnum,
                           DOME_DEVICENUM=0,
                           DOME_CHECKTIME=0.5)
        
        safetymonitor_params = dict(SAFEMONITOR_HOSTIP= '10.0.11.3',#ip_address, #'10.0.11.3'
                                    SAFEMONITOR_PORTNUM= 5565,#portnum, #5565
                                    SAFEMONITOR_DEVICENUM=0,
                                    SAFEMONITOR_CHECKTIME=0.5)
        
        target_params = dict(TARGET_MINALT=30,
                             TARGET_MAXALT=90,
                             TARGET_MOONSEP=40,
                             TARGET_SUNALT_PREPARE=-5,
                             TARGET_SUNALT_ASTRO=-18,
                             TARGET_WEIGHT_ALT = 0.5,
                             TARGET_WEIGHT_PRIORITY = 0.5)

        version_params = dict(TCSPY_VERSION='Version 3.0',
                              TCSPY_NAME='TCSpy')


        DB_params = dict(DB_HOSTIP='localhost',
                         DB_ID='hhchoi',
                         DB_PWD='lksdf1020',
                         DB_NAME='target')
        
        specmode_params = dict(SPECMODE_FOLDER=f'{self._configfilepath_global}specmode/u10/')
        
        startup_params = dict(STARTUP_ALT = 50,
                              STARTUP_AZ = 60,
                              STARTUP_CCDTEMP = -10,
                              STARTUP_CCDTEMP_TOLERANCE = 1)

        shutdown_params = dict(SHUTDOWN_ALT = 50,
                               SHUTDOWN_AZ = 60,
                               SHUTDOWN_CCDTEMP = 10,
                               SHUTDOWN_CCDTEMP_TOLERANCE = 1)
        
        make_configfile(telescope_params, filename='Telescope.config')
        make_configfile(camera_params, filename='Camera.config')
        make_configfile(filterwheel_params, filename='FilterWheel.config')
        make_configfile(focuser_params, filename='Focuser.config')
        make_configfile(observer_params, filename='Observer.config')
        make_configfile(logger_params, filename='Logger.config')
        make_configfile(image_params, filename='Image.config')
        
        # Global params
        make_configfile(version_params, filename='Version.config', savepath= self._configfilepath_global)
        make_configfile(target_params, filename='Target.config', savepath= self._configfilepath_global)
        make_configfile(weather_params, filename='Weather.config', savepath= self._configfilepath_global)
        make_configfile(dome_params, filename='Dome.config', savepath= self._configfilepath_global)
        make_configfile(safetymonitor_params, filename='SafetyMonitor.config', savepath= self._configfilepath_global)
        make_configfile(DB_params, filename = 'DB.config', savepath= self._configfilepath_global)
        make_configfile(specmode_params, filename = 'specmode.config', savepath= self._configfilepath_global)
        make_configfile(startup_params, filename = 'startup.config', savepath= self._configfilepath_global)
        make_configfile(shutdown_params, filename = 'shutdown.config', savepath= self._configfilepath_global)


        os.makedirs(image_params['IMAGE_PATH'], exist_ok=True)
        os.makedirs(logger_params['LOGGER_PATH'], exist_ok=True)


# %% Temporary running
if __name__ == '__main__':
    A = mainConfig(unitnum=11)
    A._initialize_config(ip_address='10.0.106.9', portnum = 11111)

# %%
# %%
