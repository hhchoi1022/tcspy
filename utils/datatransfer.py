


#%%
import os
from tcspy.configuration import mainConfig
import subprocess
from astropy.time import Time
#%%


class DataTransferManager(mainConfig):
    
    def __init__(self,
                 source_home_directory : str = '/data1/obsdata/',
                 destination_home_directory : str = '/large_data/obsdata/obsdata_from_mcs/'):
        super().__init__()
        self.source_homedir = source_home_directory
        self.destination_homedir = destination_home_directory
        self.server = self._set_server(**self.config)
        self.gridftp = self._set_gridftp_params(**self.config)
    
    def gridFTP_transfer(self,
                         key : str = '*/images/20240515',
                         output_file_name : str = 'temp.tar'):
        verbose_command = ''
        if self.gridftp.verbose:
            verbose_command = '-vb'
        source_path = self.tar(source_file_key= key, output_file_key = f'{os.path.join(self.source_homedir, output_file_name)}', compress = False)
        command = f"globus-url-copy {verbose_command} -p {self.gridftp.numparallel} file:{source_path} sshftp://{self.server.username}@{self.server.ip}:{self.server.portnum}{self.destination_homedir}"
        try:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Transfer successful: {result.stdout.decode()}")
        except subprocess.CalledProcessError as e:
            print(f"Error during transfer: {e.stderr.decode()}")
        return command

    def hpnscp_transfer(self,
                        key : str = '*/images/20240503',
                        output_file_name : str = 'temp.tar'):

        source_path = self.tar(source_file_key= key, output_file_key = f'{os.path.join(self.source_homedir, output_file_name)}', compress = False)
        command = f"hpnscp -P {self.server.portnum} {source_path} {self.server.username}@{self.server.ip}:{self.destination_homedir}"
        try:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Transfer successful: {result.stdout.decode()}")
        except subprocess.CalledProcessError as e:
            print(f"Error during transfer: {e.stderr.decode()}")
        return command

    def tar(self,
            source_file_key : str,
            output_file_key : str,
            compress : bool = False):
        compress_command = '-cvf'
        if compress:
            compress_command = '-cvjf'
        command = f'cd {self.source_homedir} && tar {compress_command} {output_file_key} -C {self.source_homedir} {source_file_key}'
        try:
            print(f"Tarball started: {Time.now().isot}")
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Tarball successful: {result.stdout.decode()}")
            return output_file_key
        except subprocess.CalledProcessError as e:
            print(f"Error during Tarball: {e.stderr.decode()}")
        return command

    
    def _set_server(self,
                    TRANSFER_SERVER_IP,
                    TRANSFER_SERVER_USERNAME,
                    TRANSFER_SERVER_PORTNUM,
                    **kwrags
                    ):    
        class server: 
            ip = TRANSFER_SERVER_IP
            username = TRANSFER_SERVER_USERNAME
            portnum = TRANSFER_SERVER_PORTNUM
            def __repr__(self): 
                return ('SERVER CONFIGURATION ============\n'
                        f'server.ip = {self.ip}\n'
                        f'server.username = {self.username}\n'
                        f'server.portnum = {self.portnum}\n' 
                        '=================================')
        return server()
        
    def _set_gridftp_params(self,
                            TRANSFER_GRIDFTP_NUMPARALLEL : int = 128, # Number of parallel data connection
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
A.gridFTP_transfer(key = '*/images/2024-05-09_gain2750', output_file_name= '2024-05-09_gain2750.tar')
# %%
