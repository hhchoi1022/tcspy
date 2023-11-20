# Written by Hyeonho Choi 2022.12
#%%
import logging
import logging.handlers
from tcspy.configuration import mainConfig
import datetime
import os
#%%
class mainLogger(mainConfig):
    def __init__(self,
                 unitnum : int,
                 logger_name,
                 **kwargs
                 ):
        
        super().__init__(unitnum= unitnum)
        self._log = self.createlogger(logger_name)
    
    def log(self):
        return self._log
    
    def createlogger(self,
                     logger_name):
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
            fileHandler = logging.FileHandler(filename = self.config['LOGGER_PATH']+datetime.datetime.now().strftime('%Y%m%d')+'.log')
            fileHandler.setLevel(self.config['LOGGER_LEVEL'])
            fileHandler.setFormatter(formatter)
            logger.addHandler(fileHandler)
        return logger