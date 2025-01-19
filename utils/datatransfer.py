
#%%
import time
import os
import subprocess
import glob
import re
import hashlib
from tqdm import tqdm
from astropy.time import Time
from typing import Optional
from threading import Thread
from datetime import datetime
from collections import defaultdict
from tcspy.configuration import mainConfig
#%%
class DataTransferManager(mainConfig):
    
    def __init__(self):
        super().__init__()
        self.source_homedir = self.config['TRANSFER_SOURCE_HOMEDIR']
        self.archive_homedir = self.config['TRANSFER_ARCHIVE_HOMEDIR']
        self.server_homedir = self.config['TRANSFER_SERVER_HOMEDIR']
        self.server = self._set_server(**self.config)
        self.gridftp = self._set_gridftp_params(**self.config)
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.too_last_seen = None
        
    def start_monitoring(self, ordinary_file_key = '*/image/*', ToO_file_key = '*/image/*_ToO', inactivity_period = 1800, save_hash = True, tar = True, transfer = True, move_and_clean = True, protocol = 'gridftp'):
        """Monitor files and initiate transfers."""
        print(f'Monitoring started since {Time.now().isot}')
        while True:
            current_time = datetime.now()
            
            # Check for ordinary file transfer at 8 AM local time
            if current_time.hour == 12 and current_time.minute == 0:
                self.transfer_ordinary_files(ordinary_file_key = ordinary_file_key, tar = tar, protocol = protocol)

            # Check for ToO file transfer based on inactivity (no new files for 30 minutes)
            self.transfer_ToO_files(inactivity_period = inactivity_period, ToO_file_key = ToO_file_key, save_hash= save_hash, tar = tar, transfer = transfer, move_and_clean = move_and_clean, protocol = protocol)

            # Sleep for a minute before checking again
            time.sleep(60)

    def transfer_ordinary_files(self, ordinary_file_key = '*/image/*', save_hash = True, tar = True, transfer = True, move_and_clean = True, protocol = 'gridftp'):
        """Transfer ordinary files at 8 AM."""
        # Transfer all files with ordinary criteria
        print(f"Ordinary file transfer triggered at {Time.now().isot}")
        folder_list = set([os.path.basename(folder) for folder in (glob.glob(os.path.join(self.source_homedir, ordinary_file_key)))])
        if len(folder_list) > 0:
            print(f"Transferring ordinary files at {Time.now().isot}")
            for folder in folder_list:
                key = os.path.join(os.path.dirname(ordinary_file_key), folder)
                print('Transferring folder:', key)
                self.run(key = key, save_hash = save_hash, tar = tar, transfer = True, move_and_clean = True, protocol = protocol, thread = False)
        
    def transfer_ToO_files(self, inactivity_period, ToO_file_key = '*/image/*_ToO', save_hash = True, tar = True, transfer = True, move_and_clean = True, protocol = 'gridftp'):
        """Transfer ToO files after 30 minutes of inactivity."""
        too_files = glob.glob(os.path.join(self.source_homedir, ToO_file_key, '*'))
        folder_list = set([os.path.basename(os.path.dirname(file_)) for file_ in too_files])
        if too_files:
            print("ToO files found. Waiting for inactivity...")
            latest_file_time = max([os.path.getmtime(file_) for file_ in too_files])

            if self.too_last_seen is None or latest_file_time > self.too_last_seen:
                self.too_last_seen = latest_file_time

            if time.time() - self.too_last_seen >= inactivity_period:
                print(f'Transferring ToO files at {Time.now().isot}')
                for folder in folder_list:
                    key = os.path.join(os.path.dirname(ToO_file_key), folder)
                    print(f"Transferring ToO folder: {key}")
                    self.run(key=key, save_hash = save_hash, tar = tar, transfer = transfer, move_and_clean = move_and_clean, protocol = protocol, thread=False)
                    self.too_last_seen = None
        
    def run(self, 
            key: str = '*/image/20240515', 
            output_file_name: str = None, 
            save_hash : bool = True,
            tar : bool = True,
            transfer : bool = True,
            move_and_clean : bool = True,
            protocol = 'gridftp', 
            thread = True):
        if thread:
            if protocol == 'hpnscp':
                self.transfer_thread = Thread(target=self.gridFTP_transfer, kwargs=dict(key = key, output_file_name = output_file_name, save_hash = save_hash, tar = tar, transfer = transfer, move_and_clean = move_and_clean))
            else:            
                self.transfer_thread = Thread(target=self.hpnscp_transfer, kwargs=dict(key = key, output_file_name = output_file_name, save_hash = save_hash, tar = tar, transfer = transfer, move_and_clean = move_and_clean))
            self.transfer_thread.start()
        else:
            if protocol == 'hpnscp':
                self.hpnscp_transfer(key = key, output_file_name= output_file_name, save_hash = save_hash, tar = tar, transfer = transfer, move_and_clean = move_and_clean)
            else:
                self.gridFTP_transfer(key = key, output_file_name= output_file_name, save_hash = save_hash, tar = tar, transfer = transfer, move_and_clean = move_and_clean)
        
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
                         key : str = '*/image/20240515',
                         output_file_name : str =  None,
                         save_hash: bool = True,
                         tar : bool = True,
                         transfer : bool = True,
                         move_and_clean : bool = True):
        self.is_running = True
        if save_hash:
            self.generate_and_save_hash(source_file_key=key)
        if not output_file_name:
            output_file_name = os.path.basename(key)+'.tar'
        verbose_command = ''
        if self.gridftp.verbose:
            verbose_command = '-vb'
        if tar:
            source_path = self.tar(source_file_key= key, output_file_key = f'{os.path.join(self.archive_homedir, output_file_name)}', compress = False)
        else:
            source_path = f'{os.path.join(self.archive_homedir, output_file_name)}'
        command = f"globus-url-copy {verbose_command} -p {self.gridftp.numparallel} -rst-retries 10 -rst-interval 60 file:{source_path} sshftp://{self.server.username}@{self.server.ip}:{self.server.portnum}{self.server_homedir}"
        try:
            if transfer:
                print('GRIDFTP PROTOCOL WITH THE COMMAND:',command)
                self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = self.process.communicate()
                if self.process.returncode == 0:
                    print(f"Transfer successful: {stdout.decode()}")
                else:
                    raise RuntimeError(f"Error during transfer: {stderr.decode()}")
        except:
            self.process = None
            self.is_running = False

        if move_and_clean:
            self.move_to_archive_and_cleanup(key, source_path)
        self.process = None
        self.is_running = False

    def hpnscp_transfer(self,
                        key : str = '*/image/20240503',
                        output_file_name : str = None,
                        save_hash: bool = True,
                        tar : bool = True,
                        transfer : bool = True,
                        move_and_clean : bool = True
                        ):
        self.is_running = True
        if save_hash:
            self.generate_and_save_hash(source_file_key=key)
        if not output_file_name:
            output_file_name = os.path.basename(key)+'.tar'
        if tar:
            source_path = self.tar(source_file_key= key, output_file_key = f'{os.path.join(self.archive_homedir, output_file_name)}', compress = False)
        else:
            source_path = f'{os.path.join(self.archive_homedir, output_file_name)}'
        command = f"hpnscp -P {self.server.portnum} {source_path} {self.server.username}@{self.server.ip}:{self.server_homedir}"
        try:
            if transfer:
                print('HPNSSH PROTOCOL WITH THE COMMAND:',command)
                self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = self.process.communicate()
                if self.process.returncode == 0:
                    print(f"Transfer successful: {stdout.decode()}")
                else:
                    raise RuntimeError(f"Error during transfer: {stderr.decode()}")
        except:
            self.process = None
            self.is_running = False
            return
        if move_and_clean:
            self.move_to_archive_and_cleanup(key, source_path)
        self.process = None
        self.is_running = False

    def generate_and_save_hash(self, source_file_key: str) -> None:
        """
        Generates SHA-256 hashes for all files matching the given pattern
        and saves each hash as a separate file in the same directory.

        Parameters:
        source_file_key (str): Glob pattern to match source files (e.g., '7DT/*.fits').

        Returns:
        None
        """
        try:
            # Match all files using the provided pattern
            source_keys = os.path.join(self.source_homedir, source_file_key, '*')
            file_paths = glob.glob(source_keys)
            if not file_paths:
                raise ValueError(f"No files matched the pattern: {source_file_key}")

            telescope_path_dict = defaultdict(list)  # Initialize a dictionary with lists as default values
            pattern = r'7DT\d{2}'  # Regex to match telescope names like 7DT12, 7DT01

            # Divide the files into lists based on the telescope name
            for path in file_paths:
                if os.path.isfile(path):  # Ensure it's a file, not a directory
                    match = re.search(pattern, path)
                    if match:
                        telescope_name = match.group()
                        telescope_path_dict[telescope_name].append(path)

            for tel_name, file_paths in telescope_path_dict.items():
                hashlist = []
                filenamelist = []
                for file_path in tqdm(file_paths, desc=f'Generating hashes of {tel_name} files...'):
                    hasher = hashlib.sha256()
                    with open(file_path, 'rb') as file:
                        # Read the file in chunks to handle large files efficiently
                        for chunk in iter(lambda: file.read(4096), b""):
                            hasher.update(chunk)

                    # Generate the hash
                    file_hash = hasher.hexdigest()
                    hashlist.append(file_hash)
                    filenamelist.append(os.path.basename(file_path))

                # Save the hash to a file in the telescope directory
                tel_directory = os.path.dirname(file_paths[0])  # Get the directory of the first file for this telescope
                hash_file_path = os.path.join(tel_directory, 'allfiles.hash')
                with open(hash_file_path, 'w') as hash_file:
                    for hash_, filename in zip(hashlist, filenamelist):
                        hash_file.write(f"{hash_} {filename}\n")
                print(f"Hash generated and saved for: {tel_name} -> {hash_file_path}")

        except Exception as e:
            raise RuntimeError(f"An error occurred while generating and saving hashes: {str(e)}")

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
        
    def move_to_archive_and_cleanup(self, key, tar_path):

        source_pattern = os.path.join(self.source_homedir, key)
        source_dirs = glob.glob(source_pattern)
        
        for source_dir in tqdm(source_dirs, desc = f'Moving folders...'):
            # Extract the 7DT?? pa
            # rt of the directory path
            parent_dir = re.findall(r'7DT\d+', source_dir)[0]
            #parent_dir = os.path.basename(os.path.dirname(os.path.dirname(source_dir)))

            # Define the corresponding archive directory
            archive_dir = os.path.join(self.archive_homedir, parent_dir)
            command = f'mv {source_dir} {archive_dir}'

            try:
                self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = self.process.communicate()
                if self.process.returncode == 0:
                    pass
                else:
                    print(f"Error during Move: {stderr.decode()}")
            except subprocess.CalledProcessError as e:
                print(f"Error during Move: {e.stderr.decode()}")
            finally:
                self.process = None
        
        # Remove the tar file
        try:
            os.remove(tar_path)
            print(f"Removed tar file: {tar_path}")
        except Exception as e:
            print(f"Error removing tar file: {e}")

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
                            TRANSFER_GRIDFTP_NUMPARALLEL : int = 64, # Number of parallel data connection
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
if __name__ == '__main__':
    A = DataTransferManager()
    import time
    A.run(key = '*/image/2025-01-18_gain2750', save_hash = True, tar = True, transfer = True, move_and_clean = True, thread = False)
    time.sleep(600)
    A.run(key = '*/image/2025-01-18_gain0', save_hash = True, tar = True, transfer = True, move_and_clean = True, thread = False)
    time.sleep(600)
    A.run(key = '*/image/2025-01-17_gain0', save_hash = True, tar = True, transfer = True, move_and_clean = True, thread = False)


    #A.run(key = '*/2024-12-15_gain2750', save_hash = True, tar = True, transfer = True, move_and_clean = False, thread = False)

    #A.run(key = '*/2024-12-12_gain2750', save_hash = True, tar = True, transfer = True, move_and_clean = False, thread = False)

    #A.move_to_archive_and_cleanup(key = '*/image/2024-10-24_gain2750', tar_path = '/data1/obsdata_archive/2024-10-25_gain2750.tar')
    # A.start_monitoring(
    #     ordinary_file_key='*/image/*',   # Adjust these parameters as needed
    #     ToO_file_key='*/image/*_ToO',
    #     inactivity_period=1800,             # 30 minutes of inactivity
    #     tar=True,                        # Compress files into tar
    #     protocol='gridftp'               # File transfer protocol
    # )

# %%
