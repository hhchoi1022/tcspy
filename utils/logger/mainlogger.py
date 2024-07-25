# Written by Hyeonho Choi 2022.12
#%%
import logging
import logging.handlers
import datetime
import os
from astropy.time import Time
import  astropy.units as u

from tcspy.configuration import mainConfig
#%%
class mainLogger(mainConfig):
    """
    A class for creating and managing loggers.

    Parameters
    ----------
    unitnum : int
        The unit number.
    logger_name : str
        The name of the logger.
    **kwargs : dict, optional
        Additional keyword arguments.

    Methods
    -------
    log()
        Get the logger instance.
    createlogger(logger_name)
        Create a logger instance.
    """
    def __init__(self,
                 unitnum : int,
                 logger_name,
                 **kwargs
                 ):
        from tcspy.devices.observer import mainObserver
        super().__init__(unitnum= unitnum)
        self.observer = mainObserver()
        self._log = self.createlogger(logger_name)
    
    def log(self):
        """
        Get the logger instance.

        Returns
        -------
        logging.Logger
            The logger instance.
        """
        return self._log
    
    def createlogger(self,
                     logger_name):
        """
        Create a logger instance.

        Parameters
        ----------
        logger_name : str
            The name of the logger.

        Returns
        -------
        logging.Logger
            The created logger instance.
        """
        # Create filepath
        if not os.path.isdir(self.config['LOGGER_PATH']):
            os.makedirs(name = self.config['LOGGER_PATH'], exist_ok= True)
        
        # Create Logger
        logger = logging.getLogger(logger_name)
        # Check handler exists
        if len(logger.handlers) > 0:
            return logger # Logger already exists
        logger.setLevel(self.config['LOGGER_LEVEL'])
        formatter = logging.Formatter(datefmt = '%Y-%m-%d %H:%M:%S',fmt = self.config['LOGGER_FORMAT'])
        
        # Create Handlers
        streamHandler = logging.StreamHandler()
        streamHandler.setLevel(self.config['LOGGER_LEVEL'])
        streamHandler.setFormatter(formatter)
        logger.addHandler(streamHandler)
        if self.config['LOGGER_SAVE']:
            sunrise_astro = self.observer.tonight(time = Time.now(), horizon = -18)[1]
            filename =  (self.observer.tonight(time = Time.now(), horizon = -18)[1] - 12 * u.hour).datetime.strftime('%Y%m%d') + '.log'
            fileHandler = logging.FileHandler(filename = self.config['LOGGER_PATH']+filename)
            fileHandler.setLevel(self.config['LOGGER_LEVEL'])
            fileHandler.setFormatter(formatter)
            logger.addHandler(fileHandler)
        return logger