


#%%
import os
from tcspy.configuration import mainConfig
import subprocess
from astropy.time import Time
from typing import Optional
from threading import Thread
#%%


class DataTransferManager(mainConfig):
    
    def __init__(self,
                 source_home_directory : str = '/data1/obsdata/',
                 destination_home_directory : str = '/data/obsdata/obsdata_from_mcs/'):
        super().__init__()
        self.source_homedir = source_home_directory
        self.destination_homedir = destination_home_directory
        self.server = self._set_server(**self.config)
        self.gridftp = self._set_gridftp_params(**self.config)
        self.process: Optional[subprocess.Popen] = None
        
    def run(self, 
            key: str = '*/images/20240515', 
            output_file_name: str = None, 
            protocol = 'gridftp', 
            thread = True):
        if thread:
            if protocol == 'hpnscp':
                self.transfer_thread = Thread(target=self.gridFTP_transfer, kwargs=dict(key = key, output_file_name = output_file_name))
            else:            
                self.transfer_thread = Thread(target=self.hpnscp_transfer, kwargs=dict(key = key, output_file_name = output_file_name))
            self.transfer_thread.start()
        else:
            if protocol == 'hpnscp':
                self.hpnscp_transfer(key = key, output_file_name= output_file_name)
            else:
                self.gridFTP_transfer(key = key, output_file_name= output_file_name)
        
    def abort(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)  # Wait for the process to terminate
                print("Transfer terminated successfully.")
            except subprocess.TimeoutExpired:
                self.process.kill()
                print("Transfer forcefully killed after timeout.")
            finally:
                self.process = None
        else:
            print("No running transfer to terminate.")
            
    def gridFTP_transfer(self,
                         key : str = '*/images/20240515',
                         output_file_name : str =  None):
        if not output_file_name:
            output_file_name = os.path.basename(key)+'.tar'
        verbose_command = ''
        if self.gridftp.verbose:
            verbose_command = '-vb'
        source_path = self.tar(source_file_key= key, output_file_key = f'{os.path.join(self.source_homedir, output_file_name)}', compress = False)
        command = f"globus-url-copy {verbose_command} -p {self.gridftp.numparallel} file:{source_path} sshftp://{self.server.username}@{self.server.ip}:{self.server.portnum}{self.destination_homedir}"
        try:
            self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = self.process.communicate()
            if self.process.returncode == 0:
                print(f"Transfer successful: {stdout.decode()}")
            else:
                print(f"Error during transfer: {stderr.decode()}")
        except subprocess.CalledProcessError as e:
            print(f"Error during transfer: {e.stderr.decode()}")
        finally:
            self.process = None

    def hpnscp_transfer(self,
                        key : str = '*/images/20240503',
                        output_file_name : str = None):

        if not output_file_name:
            output_file_name = os.path.basename(key)+'.tar'
        source_path = self.tar(source_file_key= key, output_file_key = f'{os.path.join(self.source_homedir, output_file_name)}', compress = False)
        command = f"hpnscp -P {self.server.portnum} {source_path} {self.server.username}@{self.server.ip}:{self.destination_homedir}"
        try:
            self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = self.process.communicate()
            if self.process.returncode == 0:
                print(f"Transfer successful: {stdout.decode()}")
            else:
                print(f"Error during transfer: {stderr.decode()}")
        except subprocess.CalledProcessError as e:
            print(f"Error during transfer: {e.stderr.decode()}")
        finally:
            self.process = None


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
            self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = self.process.communicate()
            if self.process.returncode == 0:
                print(f"Tarball successful: {stdout.decode()}")
            else:
                print(f"Error during Tarball: {stderr.decode()}")
        except subprocess.CalledProcessError as e:
            print(f"Error during Tarball: {e.stderr.decode()}")
        finally:
            self.process = None
        return output_file_key
        
    
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
A.run(key = f'*/images/2024-06-30_gain2750', thread = False)
# %%
