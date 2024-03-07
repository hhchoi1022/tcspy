# Written by Hyeonho Choi 2023.01
# %%
import glob
import os
from astropy.io import ascii
from astropy.table import Table
import json

class mainConfig:
    def __init__(self,
                 unitnum: int,
                 configpath : str = '/home/hhchoi1022/tcspy/configuration/',
                 **kwargs):
        self.unitnum = unitnum
        self.configpath = configpath + '7DT%.2d' % self.unitnum + '/'
        configfilekey = self.configpath + '*.config'
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

    def _initialize_config(self,
                           ip_address: str = '10.0.106.6',
                           portnum : int = '11111'):
        savepath = self.configpath
        if not os.path.exists(savepath):
            os.makedirs(savepath, exist_ok=True)

        def make_configfile(dict_params,
                            filename: str,
                            savepath=savepath):
            with open(savepath + filename, 'w') as f:
                json.dump(dict_params, f, indent=4)
            print('New configuration file made : %s' % (savepath+filename))
            
        ###### ALL CONFIGURATION PARAMETERS(EDIT HERE!!!) ######
        observer_params = dict(OBSERVER_LONGITUDE= -70.7804,
                               OBSERVER_LATITUDE= -30.4704,
                               OBSERVER_ELEVATION= 1580,
                               OBSERVER_TIMEZONE= 'America/Santiago',
                               OBSERVER_NAME='Hyeonho Choi',
                               OBSERVER_OBSERVATORY='7DT%.2d' % self.unitnum
                               )
        weather_params = dict(WEATHER_HOSTIP= ip_address,
                              WEATHER_PORTNUM= portnum,
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
        
        safetymonitor_params = dict(SAFEMONITOR_HOSTIP= ip_address,
                                    SAFEMONITOR_PORTNUM=portnum,
                                    SAFEMONITOR_DEVICENUM=0,
                                    SAFEMONITOR_CHECKTIME=0.5)

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
                                  FTWHEEL_OFFSETFILE =f"{savepath}filter.offset")

        focuser_params = dict(FOCUSER_DEVICETYPE='Alpaca',  # Alpaca or PWI4
                              FOCUSER_HOSTIP= ip_address,
                              FOCUSER_PORTNUM='8220',
                              FOCUSER_DEVICENUM=0,
                              FOCUSER_MINSTEP= 2000,
                              FOCUSER_MAXSTEP= 14000,
                              FOCUSER_CHECKTIME=0.5)
                
        target_params = dict(TARGET_MINALT=30,
                             TARGET_MAXALT=90,
                             TARGET_MAX_SUNALT=None,
                             TARGET_MOONSEP=40,
                             TARGET_MAXAIRMASS=None)
        
        image_params = dict(FILENAME_FORMAT= "$$TELESCOP$$-$$UTCDATE$$-$$UTCTIME$$-$$OBJECT$$-$$FILTER$$-$$EXPTIME$$s-$$FRAMENUM$$.fits",
                            IMAGE_PATH=f'/data1/obsdata/7DT%.2d/images/'%(self.unitnum))
        
        logger_params = dict(LOGGER_SAVE=True,
                             LOGGER_LEVEL='INFO', 
                             LOGGER_FORMAT='[%(levelname)s]%(asctime)-15s | %(message)s',
                             LOGGER_PATH= f'/data1/obsdata/7DT%.2d/log/'%(self.unitnum))

        general_params = dict(TCSPY_VERSION='Version 3.0',
                              TCSPY_NAME='TCSpy')

        make_configfile(observer_params, filename='Observer.config')
        make_configfile(telescope_params, filename='Telescope.config')
        make_configfile(camera_params, filename='Camera.config')
        make_configfile(logger_params, filename='Logger.config')
        make_configfile(general_params, filename='General.config')
        make_configfile(image_params, filename='Image.config')
        make_configfile(filterwheel_params, filename='FilterWheel.config')
        make_configfile(focuser_params, filename='Focuser.config')
        make_configfile(target_params, filename='Target.config')
        make_configfile(weather_params, filename='Weather.config')
        make_configfile(dome_params, filename='Dome.config')
        make_configfile(safetymonitor_params, filename='SafetyMonitor.config')

        os.makedirs(image_params['IMAGE_PATH'], exist_ok=True)
        os.makedirs(logger_params['LOGGER_PATH'], exist_ok=True)


# %% Temporary running
if __name__ == '__main__':
    A = mainConfig(unitnum=21)
    A._initialize_config(ip_address='127.0.0.1', portnum = 32323)

# %%
# %%
