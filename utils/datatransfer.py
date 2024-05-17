


#%%
import os
from tcspy.configuration import mainConfig
import subprocess

#%%


class DataTransferManager(mainConfig):
    
    def __init__(self,
                 source_home_directory : str = '/data1/obsdata/',
                 destination_home_directory : str = '/large_data/obsdata/data1/'):
        super().__init__()
        self.source_homedir = source_home_directory
        self.destination_homedir = destination_home_directory
        self.server = self._set_server(**self.config)
        self.gridftp = self._set_gridftp_params(**self.config)
    
    def gridFTP_transfer(self,
                         key : str = '*/images/20240501'):
        verbose_command = ''
        if self.gridftp:
            verbose_command = '-vb'
        source_path = os.path.join(self.source_homedir, key)
        command = f"globus-url-copy {verbose_command} -p {self.gridftp.numparallel} file:{source_path} sshftp://{self.server.username}@{self.server.ip}:{self.server.portnum}{self.destination_homedir}"
        try:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Transfer successful: {result.stdout.decode()}")
        except subprocess.CalledProcessError as e:
            print(f"Error during transfer: {e.stderr.decode()}")
        return command

    
        
    
    def _set_server(self,
                    TRANSFER_SERVER_IP,
                    TRANSFER_SERVER_USERNAME,
                    TRANSFER_SERVER_KEY,
                    TRANSFER_SERVER_PORTNUM,
                    **kwrags
                    ):    
        class server: 
            ip = TRANSFER_SERVER_IP
            username = TRANSFER_SERVER_USERNAME
            key = TRANSFER_SERVER_KEY
            portnum = TRANSFER_SERVER_PORTNUM
            def __repr__(self): 
                return ('SERVER CONFIGURATION ============\n'
                        f'server.ip = {self.ip}\n'
                        f'server.username = {self.username}\n'
                        f'server.key = {self.key}\n'
                        f'server.portnum = {self.portnum}\n' 
                        '=================================')
        return server()
        
    def _set_gridftp_params(self,
                            TRANSFER_GRIDFTP_NUMPARALLEL : int = 30, # Number of parallel data connection
                            TRANSFER_GRIPFTP_VERBOSE : bool = True, # Verbose?
                            TRANSFER_GRIDFTP_RETRIES : int = 10, # Number of retries
                            TRANSFER_GRIDFTP_RTINTERVAL : int = 60, # Interval in seconds before retry                           
                            **kwrags
                            ):
        class gridftp: 
            numparallel = TRANSFER_GRIDFTP_NUMPARALLEL
            verbose = TRANSFER_GRIPFTP_VERBOSE
            numretries = TRANSFER_GRIDFTP_RETRIES
            retryinterval = TRANSFER_GRIDFTP_RTINTERVAL
            def __repr__(self): 
                return ('GRIDFTP CONFIGURATION ============\n'
                        f'gridftp.numparallel = {self.numparallel}\n'
                        f'gridftp.verbose = {self.verbose}\n'
                        f'gridftp.numretries = {self.numretries}\n'
                        f'gridftp.retryinterval = {self.retryinterval}\n' 
                        '=================================')
        return gridftp()
    
    
    
    
    
        
    
# %%
DataTransferManager().gridFTP_transfer()
# %%
