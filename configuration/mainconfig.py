# Written by Hyeonho Choi 2023.01
# %%
import glob
import os
from astropy.io import ascii
import json

class mainConfig:
    def __init__(self,
                 unitnum: int = None,
                 configpath : str = '/home/kds/tcspy/configuration',
                 **kwargs):
        self.unitnum = unitnum
        self.config = dict()
                
        # global config params
        self.path_global = configpath
        self._configfilekey_global = os.path.join(self.path_global, '*.config')
        self._configfiles_global = glob.glob(self._configfilekey_global)
            
        if not os.path.isfile(os.path.join(self.path_global, 'TCSpy.config')):
            self.make_configfile(self.tcspy_params, filename='TCSpy.config', savepath= self.path_global)
            raise RuntimeError(f'TCSpy.config must be located in the configuration folder. \n New TCSpy.config file is created: {os.path.join(self.path_global, "TCSpy.config")} ')
        else:
            config_global = self._load_configuration(self._configfiles_global)
            self.config.update(config_global)
        
        if self.unitnum:
            # Specified units config params
            self.tel_name = self.config["TCSPY_TEL_NAME"] + '%.2d' % self.unitnum
            self.path_unit = os.path.join(configpath, self.tel_name)
            self._configfilekey_unit = os.path.join(self.path_unit, '*.config')
            self._configfiles_unit = glob.glob(self._configfilekey_unit)
            if len(self._configfiles_unit) == 0:
                print('No configuration file is found.\nTo make default configuration files, run tcspy.configuration.make_config')
            else:
                config_unit = self._load_configuration(self._configfiles_unit)
                self.config.update(config_unit)

    def _load_configuration(self, 
                            configfiles):
        all_config = dict()
        for configfile in configfiles:
            with open(configfile, 'r') as f:
                config = json.load(f)
                all_config.update(config)
        return all_config

    def make_configfile(self, 
                        dict_params : dict,
                        filename: str,
                        savepath : str):
        filepath = os.path.join(savepath, filename)
        with open(filepath, 'w') as f:
            json.dump(dict_params, f, indent=4)
        print('New configuration file made : %s' % (filepath))
        
    @property
    def tcspy_params(self):
        tcspy_params = dict(TCSPY_VERSION='Version 1.0',
                            TCSPY_TEL_NAME='7DT')           
        return tcspy_params

    def _initialize_config(self,
                           ip_address: str = '10.0.106.6',
                           portnum : int = '11111',
                           update_focusmodel : bool = True,
                           **kwargs):
        savepath_unit = self.path_unit
        if not os.path.exists(savepath_unit):
            os.makedirs(savepath_unit, exist_ok=True)
            
        ###### ALL CONFIGURATION PARAMETERS(EDIT HERE!!!) #####
        mount_params = dict(MOUNT_DEVICETYPE='PWI4',  # Alpaca or PWI4
                            MOUNT_HOSTIP= ip_address,
                            MOUNT_PORTNUM='8220',
                            MOUNT_DEVICENUM=0,
                            MOUNT_PARKALT=40,
                            MOUNT_PARKAZ=300,
                            MOUNT_RMSRA=0.15,
                            MOUNT_RMSDEC=0.15,
                            MOUNT_CHECKTIME=0.5,
                            MOUNT_DIAMETER=0.5,
                            MOUNT_APAREA=0.196,
                            MOUNT_FOCALLENGTH=1537.0,
                            MOUNT_FOCALRATIO=3,
                            MOUNT_SETTLETIME=3, #seconds
                            MOUNT_NAME= self.tel_name
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
                                  FTWHEEL_OFFSETFILE =f"{os.path.join(savepath_unit,'filter.offset')}")

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
                               OBSERVER_NAME='Hyeonho Choi'
                               )
        
        image_params = dict(FOLDERNAME_FORMAT = "$$UTCDATE12-$$_gain$$GAIN$$",
                            FILENAME_FORMAT= "$$TELESCOP$$_$$UTCDATE$$_$$UTCTIME$$_$$OBJECT$$_$$FILTER$$_$$XBINNING$$x$$YBINNING$$_$$EXPTIME$$s_$$FRAMENUM$$",
                            IMAGE_PATH=f'/data2/obsdata/{self.tel_name}/image/',
                            IMAGE_SAVEHEADER = True,
                            IMAGE_FORMAT = 'FITS'
                            )
        
        logger_params = dict(LOGGER_SAVE=True,
                             LOGGER_LEVEL='INFO', 
                             LOGGER_FORMAT=f'[%(levelname)s,{self.tel_name}]%(asctime)-15s |%(message)s',
                             LOGGER_PATH= f'/data2/obsdata/{self.tel_name}/log/')
        
        # Share configuration

        transfer_params = dict(TRANSFER_SERVER_IP= '210.117.217.71',
                               TRANSFER_SERVER_USERNAME = 'hhchoi1022', 
                               TRANSFER_SERVER_PORTNUM = '8022',
                               TRANSFER_SOURCE_HOMEDIR = '/data2/obsdata/',
                               TRANSFER_ARCHIVE_HOMEDIR = '/data1/obsdata_archive/',
                               TRANSFER_SERVER_HOMEDIR = '/data/obsdata/obsdata_from_mcs/',
                               TRANSFER_GRIDFTP_NUMPARALLEL = 128,
                               TRANSFER_GRIPFTP_VERBOSE = True,
                               TRANSFER_GRIDFTP_RETRIES = 10,
                               TRANSFER_GRIDFTP_RTINTERVAL = 60
                               )
        
        weather_params = dict(WEATHER_HOSTIP= '10.0.11.3',#ip_address, #'10.0.11.3'
                              WEATHER_PORTNUM= 5575,#portnum, #5575
                              WEATHER_DEVICENUM=0,
                              WEATHER_UPDATETIME=60,
                              WEATHER_PATH= f'/data2/obsdata/weather_history/',
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
        
        safetymonitor_params = dict(SAFEMONITOR_HOSTIP= '10.0.11.3', #ip_address, #'10.0.11.3'
                                    SAFEMONITOR_PORTNUM= 5565,#portnum, #5565
                                    SAFEMONITOR_DEVICENUM=0,
                                    SAFEMONITOR_UPDATETIME=60,
                                    SAFEMONITOR_PATH= f'/data2/obsdata/safetymonitor_history/')
        
        target_params = dict(TARGET_MINALT=27,
                             TARGET_MAXALT=90,
                             TARGET_MOONSEP=40,
                             TARGET_WEIGHT_ALT = 0.5,
                             TARGET_WEIGHT_PRIORITY = 0.5)

        DB_params = dict(DB_HOSTIP='localhost',
                         DB_ID='hhchoi',
                         DB_PWD='gusgh1020!', # gusgh1020! for MCS, lksdf1020 for Lnx
                         DB_NAME='target',
                         DB_PATH= f'/data2/obsdata/DB_history')
        
        autofocus_params = dict(AUTOFOCUS_FILTINFO_FILE=f'{os.path.join(self.path_global,"filtinfo.data")}',
                                AUTOFOCUS_FOCUSHISTORY_PATH = self.path_global,
                                AUTOFOCUS_TOLERANCE = 45)
        
        autoflat_params = dict(AUTOFLAT_ALTITUDE = 40,
                               AUTOFLAT_AZIMUTH = 270,
                               AUTOFLAT_MINCOUNT = 20000,
                               AUTOFLAT_MAXCOUNT = 40000,
                               AUTOFLAT_MINEXPTIME = 0.1,
                               AUTOFLAT_MAXEXPTIME = 20,
                               AUTOFLAT_WAITDURATION = 10,
                               AUTOFLAT_FILTERORDER = ['g','r','i','m500','m525','m550','m575','m475','m450','m600','m625','m650','m675','m425','m700','m725','z','m400','m750','m775','m800','m825','m850','m875','u'] # Descending order (Brightest first)
                               )
        
        specmode_params = dict(SPECMODE_FOLDER=f'{os.path.join(self.path_global,"specmode/u10/")}')
        
        startup_params = dict(STARTUP_ALT = 30,
                              STARTUP_AZ = 90,
                              STARTUP_CCDTEMP = -10,
                              STARTUP_CCDTEMP_TOLERANCE = 1)

        shutdown_params = dict(SHUTDOWN_ALT = 30,
                               SHUTDOWN_AZ = 90,
                               SHUTDOWN_CCDTEMP = 10,
                               SHUTDOWN_CCDTEMP_TOLERANCE = 1)
        
        nightsession_params = dict(NIGHTSESSION_SUNALT_AUTOFLAT = -8,
                                   NIGHTSESSION_SUNALT_STARTUP = -5,
                                   NIGHTSESSION_SUNALT_OBSERVATION = -15,
                                   NIGHTSESSION_SUNALT_SHUTDOWN = 0)
        
        nightobs_params = dict(NIGHTOBS_SAFETYPE = 'safetymonitor',)        
        self.make_configfile(mount_params, filename='Mount.config', savepath = savepath_unit)
        self.make_configfile(camera_params, filename='Camera.config', savepath = savepath_unit)
        self.make_configfile(filterwheel_params, filename='FilterWheel.config', savepath = savepath_unit)
        self.make_configfile(focuser_params, filename='Focuser.config', savepath = savepath_unit)
        self.make_configfile(logger_params, filename='Logger.config', savepath = savepath_unit)
        self.make_configfile(image_params, filename='Image.config', savepath = savepath_unit)

        # Global params
        self.make_configfile(self.tcspy_params, filename='TCSpy.config', savepath= self.path_global)
        self.make_configfile(observer_params, filename='Observer.config', savepath= self.path_global)
        self.make_configfile(target_params, filename='Target.config', savepath= self.path_global)
        self.make_configfile(transfer_params, filename='Transfer.config', savepath= self.path_global)

        
        self.make_configfile(weather_params, filename='Weather.config', savepath= self.path_global)
        self.make_configfile(dome_params, filename='Dome.config', savepath= self.path_global)
        self.make_configfile(safetymonitor_params, filename='SafetyMonitor.config', savepath= self.path_global)
        self.make_configfile(DB_params, filename = 'DB.config', savepath= self.path_global)
        self.make_configfile(autofocus_params, filename = 'Autofocus.config', savepath= self.path_global)
        self.make_configfile(autoflat_params, filename = 'Autoflat.config', savepath= self.path_global)
        self.make_configfile(specmode_params, filename = 'specmode.config', savepath= self.path_global)
        self.make_configfile(startup_params, filename = 'startup.config', savepath= self.path_global)
        self.make_configfile(shutdown_params, filename = 'shutdown.config', savepath= self.path_global)
        self.make_configfile(nightobs_params, filename = 'nightobs.config', savepath= self.path_global)
        self.make_configfile(nightsession_params, filename = 'nightsession.config', savepath= self.path_global)

        os.makedirs(image_params['IMAGE_PATH'], exist_ok=True)
        os.makedirs(logger_params['LOGGER_PATH'], exist_ok=True)
        
        if update_focusmodel:
            from tcspy.configuration import FocusModel
            F = FocusModel(unitnum = self.unitnum, configpath = self.path_global, filtinfo_file = './filtinfo.data', offset_file = 'filter.offset')
            F.update_params()
        



#%%
if __name__ == '__main__':
    unitnumlist = [1,2,3,4,5,6,7,8,9,10,11,13,14]
    addresslist = ['10.0.106.6',
                   '10.0.106.7',
                   '10.0.106.8',
                   '10.0.106.16',
                   '10.0.106.10',
                   '10.0.106.11',
                   '10.0.106.12',
                   '10.0.106.13',
                   '10.0.106.14',
                   '10.0.106.15',
                   '10.0.106.9',
                   '10.0.106.18',
                   '10.0.106.19']
    for unitnum, address in zip(unitnumlist, addresslist):
        A = mainConfig(unitnum=unitnum)
        A._initialize_config(ip_address=address, portnum = 11111, update_focusmodel = True, calc_focusmodel = True)

# %%
if __name__ == '__main__':
    unitnumlist = [21]
    addresslist = ['127.0.0.1']
    for unitnum, address in zip(unitnumlist, addresslist):
        A = mainConfig(unitnum=unitnum)
        A._initialize_config(ip_address=address, portnum = 32323)
# %%
