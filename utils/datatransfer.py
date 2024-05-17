


#%%
import os
from tcspy.configuration import mainConfig
import subprocess
from astropy.time import Time
#%%


class DataTransferManager(mainConfig):
    
    def __init__(self,
                 source_home_directory : str = '/data1/obsdata/',
                 destination_home_directory : str = '/data/obsdata/data1/'):
        super().__init__()
        self.source_homedir = source_home_directory
        self.destination_homedir = destination_home_directory
        self.server = self._set_server(**self.config)
        self.gridftp = self._set_gridftp_params(**self.config)
    
    def gridFTP_transfer(self,
                         key : str = '*/images/20240504',
                         output_file_name : str = '/data1/temp.tar'):
        verbose_command = ''
        if self.gridftp:
            verbose_command = '-vb'
        source_abskey = os.path.join(self.source_homedir, key)
        source_path = self.tar(source_file_key= source_abskey, output_file_key = f'{os.path.join(os.path.dirname(key), output_file_name)}', compress = False)
        command = f"globus-url-copy {verbose_command} -p {self.gridftp.numparallel} file:{source_path} sshftp://{self.server.username}@{self.server.ip}:{self.server.portnum}{self.destination_homedir}"
        try:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Transfer successful: {result.stdout.decode()}")
        except subprocess.CalledProcessError as e:
            print(f"Error during transfer: {e.stderr.decode()}")
        return command

    def hpnssh_transfer(self,
                        key : str = '*/images/20240504',
                        output_file_name : str = '/data1/temp.tar'):
        pass

    def tar(self,
            source_file_key : str,
            output_file_key : str,
            compress : bool = False):
        compress_command = '-cvf'
        if compress:
            compress_command = '-cvjf'
        command = f'tar {compress_command} {output_file_key} -C {source_file_key}'
        try:
            print(f"Tarball started: {Time.now().isot}")
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Tarball successful: {result.stdout.decode()}")
            return output_file_key
        except subprocess.CalledProcessError as e:
            print(f"Error during Tarball: {e.stderr.decode()}")

    
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
A = DataTransferManager()
#%%
A.gridFTP_transfer()
# %%
