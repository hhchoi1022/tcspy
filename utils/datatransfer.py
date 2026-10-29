#%%
#%%
import time
import os
import subprocess
import glob
import re
import hashlib
import sys
from tqdm import tqdm
from astropy.time import Time
from astropy.table import Table, vstack
from astropy.io import ascii
from typing import Optional
from threading import Thread, Semaphore
import shutil
from pathlib import Path
from datetime import datetime, timezone
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
        self.rsync_processes = []
        self._abort_requested = False
        self.is_running = False
        self.too_last_seen = None
        self.too_failures = {}   # ToO folder name -> consecutive verification failures

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

    def transfer_ordinary_files(self, ordinary_file_key = '*/image/*', save_hash = True, tar = True, sync_log = True, transfer = True, move_and_clean = True, protocol = 'gridftp'):
        """Transfer ordinary files at 8 AM."""
        # Transfer all files with ordinary criteria
        print(f"Ordinary file transfer triggered at {Time.now().isot}")
        # *_ToO folders are handled by transfer_ToO_files (they may still be accumulating)
        folder_list = set([os.path.basename(folder) for folder in (glob.glob(os.path.join(self.source_homedir, ordinary_file_key)))
                           if not os.path.basename(folder).endswith('_ToO')])
        if len(folder_list) > 0:
            print(f"Transferring ordinary files at {Time.now().isot}")
            for folder in folder_list:
                key = os.path.join(os.path.dirname(ordinary_file_key), folder)
                print('Transferring folder:', key)
                self.run(key = key, save_hash = save_hash, tar = tar, sync_log = sync_log, transfer = True, move_and_clean = True, protocol = protocol)

    def transfer_ToO_files(self, inactivity_period, ToO_file_key = '*/image/*_ToO', save_hash = True, tar = True, transfer = True, move_and_clean = True, protocol = 'gridftp', max_failures = 3):
        """Transfer ToO folders once no new data file has appeared for `inactivity_period` seconds.

        - *.hash files are ignored when measuring inactivity (regenerating them must not restart the timer).
        - A folder whose transfer failed verification `max_failures` times in a row is skipped (and reported)
          until new data files arrive there; the next attempt waits a full inactivity period.
        - The same *_ToO folder is transferred once per batch during a night; history/verify handle that
          in rsync_transfer.
        """
        too_files = [file_ for file_ in glob.glob(os.path.join(self.source_homedir, ToO_file_key, '*'))
                     if not file_.endswith('.hash')]
        if not too_files:
            return
        folder_list = sorted(set([os.path.basename(os.path.dirname(file_)) for file_ in too_files]))
        latest_file_time = max([os.path.getmtime(file_) for file_ in too_files])

        if self.too_last_seen is None or latest_file_time > self.too_last_seen:
            self.too_last_seen = latest_file_time
            self.too_failures = {}   # new data arrived -> give failed folders another chance

        if time.time() - self.too_last_seen < inactivity_period:
            print("ToO files found. Waiting for inactivity...")
            return

        print(f'Transferring ToO files at {Time.now().isot}')
        for folder in folder_list:
            if self.too_failures.get(folder, 0) >= max_failures:
                print(f"[ToO] {folder}: skipped after {max_failures} consecutive verification failures. "
                      f"Waiting for new files or a manual run.")
                continue
            key = os.path.join(os.path.dirname(ToO_file_key), folder)
            print(f"Transferring ToO folder: {key}")
            ok = self.run(key=key, save_hash = save_hash, tar = tar, transfer = transfer, move_and_clean = move_and_clean, protocol = protocol, sync_log = True)
            if ok:
                self.too_failures.pop(folder, None)
            else:
                self.too_failures[folder] = self.too_failures.get(folder, 0) + 1
                n = self.too_failures[folder]
                print(f"[ToO] {folder}: transfer not verified ({n}/{max_failures})")
                if n >= max_failures:
                    self._notify(f"ToO transfer of {folder} failed verification {n} times in a row. "
                                 f"Source kept at {self.source_homedir}. Check the server and re-run manually.")
        # Whatever is left (failed or skipped) waits a full inactivity period before the next attempt
        self.too_last_seen = time.time()

    def run(self,
            key: str = '*/image/20240515',
            output_file_name: str = None,
            save_hash: bool = True,
            tar: bool = True,
            sync_log: bool = True,
            transfer: bool = True,
            move_and_clean: bool = True,
            protocol: str = 'gridftp',
            from_archive: bool = False,
            dry_run: bool = False) -> bool:
        """Run one transfer. Returns True when the transfer finished and (for rsync) verified OK.
        dry_run applies to the rsync protocol only: nothing is written, logged or moved."""
        source_dir = self.source_homedir
        if from_archive:
            self.source_homedir = self.archive_homedir
        try:
            if protocol == 'hpnscp':
                if dry_run:
                    print('[hpnscp] dry_run is not supported for this protocol; nothing done.')
                    return False
                result = self.hpnscp_transfer(key=key, output_file_name=output_file_name, save_hash=save_hash,
                                              tar=tar, sync_log=sync_log, transfer=transfer, move_and_clean=move_and_clean)
            elif protocol == 'rsync':
                result = self.rsync_transfer(key=key, output_file_name=output_file_name, save_hash=save_hash,
                                             tar=tar, sync_log=sync_log, transfer=transfer, move_and_clean=move_and_clean,
                                             dry_run=dry_run)
            else:
                if dry_run:
                    print('[gridftp] dry_run is not supported for this protocol; nothing done.')
                    return False
                result = self.gridFTP_transfer(key=key, output_file_name=output_file_name, save_hash=save_hash,
                                               tar=tar, sync_log=sync_log, transfer=transfer, move_and_clean=move_and_clean)
        finally:
            self.source_homedir = source_dir
        return bool(result)

    def gridFTP_transfer(self,
                         key : str = '*/image/20240515',
                         output_file_name : str =  None,
                         save_hash: bool = True,
                         tar : bool = True,
                         sync_log: bool = True,
                         transfer : bool = True,
                         move_and_clean : bool = True):
        self.is_running = True
        if save_hash:
            self.generate_and_save_hash(source_file_key=key)
        if not output_file_name:
            now_str = Time.now().datetime.strftime('%Y%m%d_%H%M%S')
            output_file_name = os.path.basename(key)+f'_{now_str}.tar'
        verbose_command = ''
        if self.gridftp.verbose:
            verbose_command = '-vb'
        if tar:
            source_path = self.tar(source_file_key= key, output_file_key = f'{os.path.join(self.archive_homedir, output_file_name)}', compress = False, sync_log = sync_log)
        else:
            source_path = f'{os.path.join(self.archive_homedir, output_file_name)}'
        logfile = f'/data2/obsdata/transfer_history/{Time.now().isot}.log'
        command = f"globus-url-copy {verbose_command} -fast -dbg -p {self.gridftp.numparallel} -rst-retries {self.gridftp.numretries} -rst-interval {self.gridftp.retryinterval} file:{source_path} sshftp://{self.server.username}@{self.server.ip}:{self.server.portnum}{self.server_homedir} > {logfile}"
        #try:
        if transfer:
            print('GRIDFTP PROTOCOL WITH THE COMMAND:',command)
            self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = self.process.communicate()
            if self.process.returncode == 0:
                print(f"Transfer successful: {stdout.decode()}")
            else:
                raise RuntimeError(f"Error during transfer: {stderr.decode()}")
        #except:
        #    self.process = None
        #    self.is_running = False

        if move_and_clean:
            self.move_to_archive_and_cleanup(key, source_path)
        self.process = None
        self.is_running = False
        return True

    def hpnscp_transfer(self,
                        key : str = '*/image/20240503',
                        output_file_name : str = None,
                        save_hash: bool = True,
                        tar : bool = True,
                        sync_log: bool = True,
                        transfer : bool = True,
                        move_and_clean : bool = True
                        ):
        self.is_running = True
        if save_hash:
            self.generate_and_save_hash(source_file_key=key)
        if not output_file_name:
            now_str = Time.now().datetime.strftime('%Y%m%d_%H%M%S')
            output_file_name = os.path.basename(key)+f'_{now_str}.tar'
        if tar:
            source_path = self.tar(source_file_key= key, output_file_key = f'{os.path.join(self.archive_homedir, output_file_name)}', compress = False, sync_log = sync_log)
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
            return False
        if move_and_clean:
            self.move_to_archive_and_cleanup(key, source_path)
        self.process = None
        self.is_running = False
        return True

    def rsync_transfer(self,
                       key: str = '*/image/2026-09-06_gain2750',
                       output_file_name: str = None,
                       save_hash: bool = True,
                       tar: bool = False,
                       sync_log: bool = True,
                       transfer: bool = True,
                       move_and_clean: bool = True,
                       numparallel: int = None,
                       ssh_bin: str = 'hpnssh',
                       rsync_timeout: int = 120,
                       retry_interval: int = 10,
                       dry_run: bool = False) -> bool:
        """
        Transfer per-unit directories with rsync in parallel (no tar).

        Verification checks that every local file exists on the server with the same size.
        Extra files on the server are allowed: a *_ToO folder is transferred once per batch
        during a night and the server accumulates all batches while the local copy of each
        batch is moved to the archive. The history log and move_and_clean run only when
        verification passes.

        A per-batch hash file (allfiles_<stamp>.hash) is transferred along with the data so
        the server can verify integrity with `sha256sum -c`.

        dry_run=True: no hash file is written, rsync runs with --dry-run, nothing is logged
        or moved. Verification still runs, so the printed table shows the current server state.

        (output_file_name, tar are unused args kept for signature compatibility.)
        Returns True when the transfer (or dry run) verified OK.
        """
        self.is_running = True
        self._abort_requested = False
        self.rsync_processes = []
        all_ok = True
        tag = '[rsync][dry-run]' if dry_run else '[rsync]'
        try:
            if numparallel is None:
                numparallel = self.gridftp.numparallel

            # Generate hashes before transfer (allfiles_<stamp>.hash in each unit dir)
            if save_hash and not dry_run:
                self.generate_and_save_hash(source_file_key=key)

            # Collect source dirs (per unit) matching key
            source_pattern = os.path.join(self.source_homedir, key)
            source_dirs = sorted(glob.glob(source_pattern))
            if not source_dirs:
                print(f"{tag} No source dirs matched: {source_pattern}")
                return False

            pattern = re.compile(r'7DT\d{2}')
            unit_src = {}
            for source_dir in source_dirs:
                if not os.path.isdir(source_dir):
                    continue
                match = pattern.search(source_dir)
                if match:
                    unit_src[match.group()] = source_dir
                else:
                    print(f"[rsync] Could not find telescope name, skipping: {source_dir}")

            if not unit_src:
                print(f"{tag} No unit directories to transfer.")
                return False

            ssh_command = f"{ssh_bin} -p {self.server.portnum}"

            if transfer:
                print(f"[rsync] Transfer started: {len(unit_src)} units, parallel {numparallel}")
                semaphore = Semaphore(numparallel)
                threads = []

                def worker(unit, source_dir):
                    with semaphore:
                        if self._abort_requested:
                            return
                        self._rsync_send_unit(unit, source_dir, ssh_command,
                                              rsync_timeout, retry_interval, dry_run=dry_run)

                for unit, source_dir in sorted(unit_src.items()):
                    thread = Thread(target=worker, args=(unit, source_dir))
                    thread.start()
                    threads.append(thread)

                # Timeout loop so Ctrl+C (KeyboardInterrupt) is caught even during join
                try:
                    while any(t.is_alive() for t in threads):
                        for t in threads:
                            t.join(timeout=0.5)
                except KeyboardInterrupt:
                    print("\n[rsync] KeyboardInterrupt -> aborting...")
                    self.abort()
                    for t in threads:
                        t.join(timeout=10)
                    self.is_running = False
                    raise

                if self._abort_requested:
                    print(f"{tag} Aborted by user. Skipping verify/move.")
                    return False
                print(f"{tag} All units transfer round finished")

            # Post-transfer verification: every local file present on the server with the same size
            total_files = 0
            total_bytes = 0
            if transfer:
                all_ok, total_files, total_bytes = self._rsync_verify(unit_src, ssh_command)

            if dry_run:
                print(f"{tag} Done. Nothing was written, logged or moved.")
                return all_ok

            # Log transfer history: one row per verified batch.
            # Key = <folder>_<UTC timestamp>, like the tar-era file names, so a *_ToO folder that is
            # transferred several times in one night gets one row per batch instead of being skipped.
            if sync_log and transfer and all_ok:
                try:
                    leaf = os.path.basename(next(iter(unit_src.values())).rstrip('/'))
                    date_key = f"{leaf}_{Time.now().datetime.strftime('%Y%m%d_%H%M%S')}"
                    self._log_rsync_history(date_key, unit_src, total_bytes)
                except Exception as e:
                    print(f"{tag} Failed to log transfer history: {e}")

            # Move/cleanup only if all units verified
            if move_and_clean:
                if all_ok:
                    print(f"{tag} Verification passed -> move to archive and cleanup")
                    self.move_to_archive_and_cleanup(key, tar_path='/nonexistent_rsync_no_tar')
                else:
                    print("################################################################")
                    print("## CRITICAL: Unverified unit(s) found -> skip move, keep source  ##")
                    print("################################################################")
            return all_ok

        finally:
            self.process = None
            self.rsync_processes = []
            self.is_running = False

    def abort(self):
        # If rsync parallel transfer is running, terminate all child rsync processes
        self._abort_requested = True
        if getattr(self, 'rsync_processes', None):
            for p in list(self.rsync_processes):
                try:
                    if p.poll() is None:
                        p.terminate()
                        try:
                            p.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            p.kill()
                except Exception as e:
                    print(f"Error terminating rsync process: {e}")
            self.rsync_processes = []
            print("Rsync transfer(s) terminated successfully.")

        # Terminate the single process (gridftp/hpnscp/tar) as well (original behavior)
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
                print("Transfer terminated successfully.")
            except subprocess.TimeoutExpired:
                self.process.kill()
                print("Transfer forcefully killed after timeout.")
            finally:
                self.process = None
        elif not getattr(self, 'rsync_processes', None):
            print("No running transfer to terminate.")

    def _notify(self, message: str) -> None:
        """Best-effort Slack notification (falls back to print). Never raises."""
        print(f"[notify] {message}")
        try:
            from tcspy.utils.connector import SlackConnector
            slack = SlackConnector(token_path=self.config['SLACK_TOKEN'],
                                   default_channel_id=self.config['SLACK_DEFAULT_CHANNEL'])
            slack.post_message(f'[DataTransfer] {message}')
        except Exception as e:
            print(f"[notify] Slack notification failed: {e}")

    def generate_and_save_hash(self, source_file_key: str) -> None:
        """
        Generates SHA-256 hashes for all data files matching the given pattern and saves
        them per telescope as allfiles_<stamp>.hash in the same directory, where <stamp> is
        the UTC mtime of the newest data file. Existing *.hash files are not hashed.

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

            # Divide the data files into lists based on the telescope name (skip previous hash files)
            for path in file_paths:
                if os.path.isfile(path) and not path.endswith('.hash'):
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

                # One hash file per batch, named after the newest data file, so that
                #  - retrying the same batch rewrites the same file (no clutter), and
                #  - a *_ToO folder transferred in several batches keeps every batch's hashes on the
                #    server and in the archive (a fixed 'allfiles.hash' used to be overwritten).
                tel_directory = os.path.dirname(file_paths[0])  # Get the directory of the first file for this telescope
                newest_mtime = max(os.path.getmtime(p) for p in file_paths)
                stamp = datetime.fromtimestamp(newest_mtime, tz=timezone.utc).strftime('%Y%m%d_%H%M%S')
                hash_file_path = os.path.join(tel_directory, f'allfiles_{stamp}.hash')
                with open(hash_file_path, 'w') as hash_file:
                    for hash_, filename in zip(hashlist, filenamelist):
                        hash_file.write(f"{hash_} {filename}\n")
                print(f"Hash generated and saved for: {tel_name} -> {hash_file_path}")

        except Exception as e:
            raise RuntimeError(f"An error occurred while generating and saving hashes: {str(e)}")

    def tar(self,
            source_file_key: str,
            output_file_key: str,
            compress: bool = False,
            sync_log: bool = True):
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
                return  # stop if tar fails
        except subprocess.CalledProcessError as e:
            print(f"Error during Tarball: {e.stderr.decode()}")
            return
        finally:
            self.process = None

        if sync_log:
            try:
                tar_full_path = os.path.abspath(output_file_key)
                tar_size = os.path.getsize(tar_full_path)
                timestamp = Time.now()
                time_str = timestamp.strftime('%Y%m%d%H%M%S')
                iso_time = timestamp.isot
                log_folder = self.config['TRANSFER_SYNCFOLDER']
                log_file = os.path.join(log_folder, 'transfer_history.ascii_fixed_width')

                # 1. Create filelist
                filelist_filename = f"{time_str}.filelist"
                filelist_path = os.path.join(log_folder, filelist_filename)

                list_command = f"tar -tf {tar_full_path}"
                result = subprocess.run(list_command, shell=True, capture_output=True, text=True)

                # Extract only basenames (ignore directory paths)
                filelist = [
                    os.path.basename(line.strip())
                    for line in result.stdout.strip().split('\n')
                    if line.strip()  # skip empty lines
                ]

                # Save to file
                with open(filelist_path, 'w') as flist:
                    flist.write('\n'.join(filelist) + '\n')

                # 2. Check existing log
                if os.path.exists(log_file):
                    sync_history = ascii.read(log_file, format='fixed_width')
                    existing_names = sync_history['Filename'].tolist()
                else:
                    sync_history = Table(names=['Filename', 'Size', 'Time', 'File_folder'],
                                        dtype=['str', 'str', 'str', 'str'])
                    existing_names = []

                # 3. Append if not already in log
                basename = os.path.basename(tar_full_path)
                if basename not in existing_names:
                    new_row = Table(
                        [[basename], [f"{tar_size} bytes"], [iso_time], [filelist_filename]],
                        names=['Filename', 'Size', 'Time', 'File_folder']
                    )
                    updated_table = vstack([sync_history, new_row])
                    ascii.write(updated_table, log_file, format='fixed_width', overwrite=True)
                    print(f"Tar file info logged at: {log_file}")
                    print(f"File list saved at: {filelist_path}")
                else:
                    print(f"{basename} already exists in log. Skipping log update.")
            except Exception as e:
                print(f"Failed to log tar file info or save file list: {e}")
        return output_file_key

    def move_to_archive_and_cleanup(self, key, tar_path):
        source_pattern = os.path.join(self.source_homedir, key)
        source_dirs = glob.glob(source_pattern)

        for source_dir in tqdm(source_dirs, desc='Moving folders...'):
            source_dir = Path(source_dir)

            match = re.findall(r'7DT\d+', str(source_dir))
            if not match:
                print(f"Could not find telescope name in path: {source_dir}")
                continue

            parent_dir = match[0]
            archive_parent = Path(self.archive_homedir) / parent_dir
            destination_dir = archive_parent / source_dir.name

            archive_parent.mkdir(parents=True, exist_ok=True)

            try:
                if not destination_dir.exists():
                    shutil.move(str(source_dir), str(destination_dir))
                    print(f"Moved folder: {source_dir} -> {destination_dir}")

                else:
                    print(f"Destination exists. Moving files into: {destination_dir}")

                    for item in source_dir.iterdir():
                        target = destination_dir / item.name

                        if target.exists():
                            print(f"Skipping existing item: {target}")
                            continue

                        shutil.move(str(item), str(target))

                    # Remove the source folder after moving/skipping contents
                    shutil.rmtree(source_dir)
                    print(f"Removed source folder: {source_dir}")

            except Exception as e:
                print(f"Error during move: {e}")

        try:
            os.remove(tar_path)
            print(f"Removed tar file: {tar_path}")
        except Exception as e:
            print(f"Error removing tar file: {e}")

    def _rsync_send_unit(self, unit, source_dir, ssh_command, rsync_timeout, retry_interval, dry_run=False):
        """Transfer one unit directory with rsync. On interruption, auto-resume with --append.
        dry_run=True runs rsync once with --dry-run --itemize-changes and prints what would be sent."""
        source_path = source_dir.rstrip('/')  # no trailing slash -> leaf folder is created at destination
        rel_parent, _leaf = self._rel_parent_and_leaf(source_path)  # image presence handled automatically
        rel_parent_slash = (rel_parent + '/') if rel_parent else ''
        destination = (f"{self.server.username}@{self.server.ip}:"
                       f"{self.server_homedir.rstrip('/')}/{rel_parent_slash}")

        if not dry_run:
            # Ensure destination parent directory exists
            mkdir_command = (f"{ssh_command} {self.server.username}@{self.server.ip} "
                             f"'mkdir -p {self.server_homedir.rstrip('/')}/{rel_parent_slash}'")
            subprocess.run(mkdir_command, shell=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        rsync_flags = "-a --partial --inplace --append"
        if dry_run:
            rsync_flags += " --dry-run --itemize-changes"
        command = (f"rsync {rsync_flags} "
                   f"--timeout={rsync_timeout} "
                   f"-e '{ssh_command}' '{source_path}' '{destination}'")

        if dry_run:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            # itemize lines starting with '>f' / '<f' are files that would be transferred
            pending = [l for l in result.stdout.splitlines() if l[:2] in ('>f', '<f')]
            if result.returncode != 0:
                print(f"[rsync][dry-run] {unit}: rsync failed (rc={result.returncode}) {result.stderr.strip()[:200]}")
            elif pending:
                print(f"[rsync][dry-run] {unit}: {len(pending)} file(s) would be sent")
                for l in pending[:5]:
                    print(f"    {l}")
                if len(pending) > 5:
                    print(f"    ... and {len(pending) - 5} more")
            else:
                print(f"[rsync][dry-run] {unit}: nothing to send (server already up to date)")
            return

        max_retries = getattr(self.gridftp, 'numretries', 60) or 60
        fatal_codes = {1, 2, 3, 4}  # syntax/protocol/file-select/requested-action = not worth retrying
        tries = 0
        while True:
            if self._abort_requested:
                print(f"[rsync] {unit} aborted")
                return
            process = subprocess.Popen(command, shell=True)
            self.rsync_processes.append(process)
            process.wait()
            try:
                self.rsync_processes.remove(process)
            except ValueError:
                pass

            if self._abort_requested:
                print(f"[rsync] {unit} aborted")
                return
            if process.returncode == 0:
                print(f"[rsync] {unit} done")
                return
            if process.returncode in fatal_codes:
                print(f"[rsync] {unit} fatal error (rc={process.returncode}) - not retrying")
                return
            tries += 1
            if tries > max_retries:
                print(f"[rsync] {unit} exceeded {max_retries} retries - giving up "
                      f"(will be caught as mismatch in verify)")
                return
            print(f"[rsync] {unit} interrupted (rc={process.returncode}, retry {tries}/{max_retries}), "
                  f"restart in {retry_interval}s")
            time.sleep(retry_interval)

    def _rel_parent_and_leaf(self, source_dir: str):
        """
        From an absolute source path, extract the "relative parent after the unit (7DT??)"
        and the "leaf folder name". This reproduces the source structure on the server
        regardless of image presence (normal transfer / archive re-transfer).
          .../7DT01/image/2026-09-06_gain2750 -> ('7DT01/image', '2026-09-06_gain2750')
          .../7DT01/2026-09-06_gain2750       -> ('7DT01',       '2026-09-06_gain2750')
        If no unit name is found, returns ('', basename).
        """
        source_path = source_dir.rstrip('/')
        parts = source_path.split(os.sep)
        unit_idx = None
        for j in range(len(parts) - 1, -1, -1):
            if re.fullmatch(r'7DT\d{2}', parts[j]):
                unit_idx = j
                break
        if unit_idx is None:
            return '', os.path.basename(source_path)
        rel_parts = parts[unit_idx:]
        leaf = rel_parts[-1]
        rel_parent = '/'.join(rel_parts[:-1])
        return rel_parent, leaf

    def _rsync_verify(self, unit_src: dict, ssh_command: str):
        """
        Verify per unit that every local file exists on the server with the same size.
        Extra files on the server are allowed (earlier batches of the same *_ToO folder,
        whose local copies were already moved to the archive).
        Returns: (all_ok: bool, total_source_files: int, total_source_bytes: int)
        """
        all_ok = True
        total_count = 0
        total_bytes = 0
        print(f"{'UNIT':8} | {'SRC#':>6} {'SRC_BYTES':>14} | {'DST#':>6} | "
              f"{'MISSING':>7} {'SIZE!=':>6} | OK?")
        print("-" * 78)
        for unit, source_dir in sorted(unit_src.items()):
            local = {}
            for root, _, files in os.walk(source_dir):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    try:
                        local[os.path.relpath(filepath, source_dir)] = os.path.getsize(filepath)
                    except OSError:
                        pass
            source_count = len(local)
            source_bytes = sum(local.values())
            total_count += source_count
            total_bytes += source_bytes

            # Compute remote path with the same relative-path rule as transfer (image auto)
            rel_parent, leaf = self._rel_parent_and_leaf(source_dir)
            rel = f"{rel_parent}/{leaf}" if rel_parent else leaf
            remote_dir = f"{self.server_homedir.rstrip('/')}/{rel}"
            # %P = path relative to remote_dir, %s = size in bytes (GNU find)
            remote_command = (
                f"{ssh_command} {self.server.username}@{self.server.ip} "
                f"\"find '{remote_dir}' -type f -printf '%P\\t%s\\n' 2>/dev/null\""
            )
            remote = None
            try:
                result = subprocess.run(remote_command, shell=True, capture_output=True,
                                        text=True, timeout=120)
                if result.returncode == 255:   # ssh could not connect
                    raise RuntimeError(result.stderr.strip()[:200] or 'ssh connection failed')
                remote = {}
                for line in result.stdout.splitlines():
                    if '\t' in line:
                        path, size = line.rsplit('\t', 1)
                        remote[path] = int(size)
            except Exception as e:
                print(f"[rsync] {unit} remote query failed: {e}")

            if remote is None:
                ok, missing, mismatched, dest_count = False, sorted(local), [], -1
            else:
                missing = sorted(f for f in local if f not in remote)
                mismatched = sorted(f for f, s in local.items() if f in remote and remote[f] != s)
                dest_count = len(remote)
                ok = not missing and not mismatched
            if not ok:
                all_ok = False
            print(f"{unit:8} | {source_count:6d} {source_bytes:14d} | {dest_count:6d} | "
                  f"{len(missing):7d} {len(mismatched):6d} | {'OK' if ok else '!! MISMATCH'}")
            for f in missing[:3]:
                print(f"         missing on server: {f}")
            for f in mismatched[:3]:
                print(f"         size differs:      {f} (local {local[f]}, server {remote[f]})")
        print("-" * 78)
        print("=> All units verified" if all_ok else "=> Unverified unit(s) found")
        return all_ok, total_count, total_bytes

    def _log_rsync_history(self, date_key: str, unit_src: dict, total_bytes: int):
        """
        Append one rsync transfer (one date) as a single row to the existing transfer_history.
        Same schema: Filename / Size / Time / File_folder
          - Filename    : date key (e.g. 2026-09-06_gain2750)  [replaces tar filename]
          - Size        : '<total_bytes> bytes'
          - Time        : ISO time
          - File_folder : <time_str>.filelist  (full file list saved separately)
        """
        timestamp = Time.now()
        time_str = timestamp.strftime('%Y%m%d%H%M%S')
        iso_time = timestamp.isot
        log_folder = self.config['TRANSFER_SYNCFOLDER']
        log_file = os.path.join(log_folder, 'transfer_history.ascii_fixed_width')

        # 1) Save filelist (all units' files, prefixed by unit name)
        filelist_filename = f"{time_str}.filelist"
        filelist_path = os.path.join(log_folder, filelist_filename)
        filelist = []
        for unit, source_dir in sorted(unit_src.items()):
            for root, _, files in os.walk(source_dir):
                for filename in files:
                    filelist.append(f"{unit}/{filename}")
        with open(filelist_path, 'w') as flist:
            flist.write('\n'.join(filelist) + '\n')

        # 2) Read existing log
        if os.path.exists(log_file):
            sync_history = ascii.read(log_file, format='fixed_width')
            existing_names = sync_history['Filename'].tolist()
        else:
            sync_history = Table(names=['Filename', 'Size', 'Time', 'File_folder'],
                                 dtype=['str', 'str', 'str', 'str'])
            existing_names = []

        # 3) Append if the same date key is not already present
        if date_key not in existing_names:
            new_row = Table(
                [[date_key], [f"{total_bytes} bytes"], [iso_time], [filelist_filename]],
                names=['Filename', 'Size', 'Time', 'File_folder']
            )
            updated_table = vstack([sync_history, new_row])
            ascii.write(updated_table, log_file, format='fixed_width', overwrite=True)
            print(f"Transfer info logged at: {log_file}")
            print(f"File list saved at: {filelist_path}")
        else:
            print(f"{date_key} already exists in log. Skipping log update.")

    def _list_source_dates(self, base_key: str):
        """
        Collect date folder names under base_key (e.g. '*/image' or '*') across all units,
        deduplicate, sort, and return. Used for numeric selection in the CLI.
        """
        pattern = os.path.join(self.source_homedir, base_key, '*')
        dates = set()
        for path in glob.glob(pattern):
            if os.path.isdir(path):
                dates.add(os.path.basename(path))
        return sorted(dates)

    def _prompt_cli_args(self):
        """
        Interactively collect run() arguments. (Used only when running the CLI without args.)
        Returns: a list of dicts to pass to run() (multiple entries if multiple dates selected).
        """
        def ask(msg, default):
            ans = input(f"{msg} [{default}]: ").strip()
            return ans if ans else str(default)

        def ask_bool(msg, default):
            d = 'y' if default else 'n'
            ans = input(f"{msg} [y/n] (default: {d}): ").strip().lower()
            if not ans:
                return default
            return ans in ('y', 'yes', 'true', '1')

        # 1) protocol
        protocol = ask("Protocol (gridftp/hpnscp/rsync)", "rsync")

        # 2) from_archive
        from_archive = ask_bool("From archive? (re-transfer from archive)", False)

        # 3) Show date list (archive-based if from_archive, else source-based)
        original_home = self.source_homedir
        if from_archive:
            self.source_homedir = self.archive_homedir
            base_key = '*'
        else:
            base_key = '*/image'
        dates = self._list_source_dates(base_key)
        self.source_homedir = original_home  # restore (actual transfer handled by run(from_archive=))

        if not dates:
            print(f"Warning: no date folders found under '{base_key}'.")
            manual = input("Enter the key manually (e.g. */image/2026-09-06_gain2750): ").strip()
            selected_keys = [manual] if manual else []
        else:
            print("\n=== Available dates ===")
            for i, dt in enumerate(dates, 1):
                print(f"  {i:2d}) {dt}")
            raw = input(f"\nSelect date number(s) [1-{len(dates)}] (comma/range ok, e.g. 1,3,5 or 1-4): ").strip()
            picked = set()
            for part in raw.split(','):
                part = part.strip()
                if not part:
                    continue
                if re.fullmatch(r'\d+-\d+', part):
                    a, b = map(int, part.split('-'))
                    if a > b:
                        a, b = b, a
                    picked.update(range(a, b + 1))
                elif part.isdigit():
                    picked.add(int(part))
                else:
                    print(f"Ignoring invalid input: {part}")
            selected_dates = [dates[n - 1] for n in sorted(picked) if 1 <= n <= len(dates)]
            selected_keys = [os.path.join(base_key, dt) for dt in selected_dates]

        if not selected_keys:
            print("No date selected. Exiting.")
            return []

        # 4) Remaining options (with defaults)
        save_hash = ask_bool("save_hash?", True)
        tar = ask_bool("tar? (ignored for rsync)", False if protocol == 'rsync' else True)
        sync_log = ask_bool("sync_log? (record transfer history)", True)
        transfer = ask_bool("transfer? (actually run the transfer)", True)
        move_and_clean = ask_bool("move_and_clean? (move to archive after verification)",
                                  False if from_archive else True)
        dry_run = ask_bool("dry_run? (rsync only: rsync -n + verify, no hash/log/move)", False) if protocol == 'rsync' else False

        print("\n=== Run summary ===")
        print(f"  protocol       : {protocol}")
        print(f"  from_archive   : {from_archive}")
        print(f"  keys           : {selected_keys}")
        print(f"  save_hash      : {save_hash}")
        print(f"  tar            : {tar}")
        print(f"  sync_log       : {sync_log}")
        print(f"  transfer       : {transfer}")
        print(f"  move_and_clean : {move_and_clean}")
        print(f"  dry_run        : {dry_run}")
        go = ask_bool("\nProceed with this?", True)
        if not go:
            print("Cancelled.")
            return []

        return [dict(key=k, protocol=protocol, from_archive=from_archive,
                     save_hash=save_hash, tar=tar, sync_log=sync_log,
                     transfer=transfer, move_and_clean=move_and_clean, dry_run=dry_run)
                for k in selected_keys]

    def _prompt_monitoring_args(self):
        """
        Interactively collect start_monitoring arguments. (Used only when monitoring is chosen in the CLI.)
        Each item has a default; pressing Enter uses the default.
        Returns: a dict to pass to start_monitoring().
        (Once the monitoring loop starts, nothing is asked inside it.)
        """
        def ask(msg, default):
            ans = input(f"{msg} [{default}]: ").strip()
            return ans if ans else str(default)

        def ask_bool(msg, default):
            d = 'y' if default else 'n'
            ans = input(f"{msg} [y/n] (default: {d}): ").strip().lower()
            if not ans:
                return default
            return ans in ('y', 'yes', 'true', '1')

        def ask_int(msg, default):
            ans = input(f"{msg} [{default}]: ").strip()
            if not ans:
                return default
            try:
                return int(ans)
            except ValueError:
                print(f"Not an integer; using default ({default})")
                return default

        print("\n=== Monitoring settings (Enter = default) ===")
        protocol = ask("Protocol (gridftp/hpnscp/rsync)", "rsync")
        ordinary_file_key = ask("Ordinary file key", "*/image/*")
        ToO_file_key = ask("ToO file key", "*/image/*_ToO")
        inactivity_period = ask_int("ToO inactivity_period (seconds)", 1800)
        save_hash = ask_bool("save_hash?", True)
        tar = ask_bool("tar? (ignored for rsync)", False if protocol == 'rsync' else True)
        transfer = ask_bool("transfer? (actually run the transfer)", True)
        move_and_clean = ask_bool("move_and_clean? (move to archive after verification)", True)

        print("\n=== Monitoring run summary ===")
        print(f"  protocol          : {protocol}")
        print(f"  ordinary_file_key : {ordinary_file_key}")
        print(f"  ToO_file_key      : {ToO_file_key}")
        print(f"  inactivity_period : {inactivity_period}")
        print(f"  save_hash         : {save_hash}")
        print(f"  tar               : {tar}")
        print(f"  transfer          : {transfer}")
        print(f"  move_and_clean    : {move_and_clean}")
        go = ask_bool("\nStart monitoring with these settings?", True)
        if not go:
            print("Cancelled.")
            return None

        return dict(ordinary_file_key=ordinary_file_key, ToO_file_key=ToO_file_key,
                    inactivity_period=inactivity_period, save_hash=save_hash,
                    tar=tar, transfer=transfer, move_and_clean=move_and_clean,
                    protocol=protocol)

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


#%%
if __name__ == '__main__':
    A = DataTransferManager()

    try:
        # First: mode selection (monitoring vs one-shot transfer)
        mode = input("Select mode - [1] One-shot transfer  [2] Start monitoring (default: 1): ").strip() or '1'

        if mode == '2':
            # Monitoring: ask settings only before starting; ask nothing once in the loop.
            mon_args = A._prompt_monitoring_args()
            if mon_args:
                print("\n>>> Monitoring started (Ctrl+C to stop)")
                A.start_monitoring(**mon_args)
        else:
            # One-shot transfer: each item has a default. Multiple dates can be selected.
            jobs = A._prompt_cli_args()
            for job in jobs:
                print(f"\n>>> Running: {job['key']}  (protocol={job['protocol']})")
                A.run(**job)
            print("\nAll jobs done.")

    except KeyboardInterrupt:
        # Ctrl+C during transfer/monitoring -> abort then exit
        print("\n[main] KeyboardInterrupt -> running abort")
        A.abort()
        sys.exit(130)

    # ---- Note: the old style of calling directly in code still works ----
    # A.run(key='*/image/2026-09-06_gain2750', save_hash=True, tar=True,
    #       sync_log=True, transfer=True, move_and_clean=False,
    #       protocol='rsync', from_archive=False)
    # A.start_monitoring(ordinary_file_key='*/image/*', ToO_file_key='*/image/*_ToO',
    #                    inactivity_period=600, tar=True, protocol='gridftp')

    # ---- 참고: 코드에서 직접 호출하는 예전 방식도 그대로 가능 ----
    # A.run(key='*/image/2026-09-06_gain2750', save_hash=True, tar=True,
    #       sync_log=True, transfer=True, move_and_clean=False,
    #       protocol='rsync', from_archive=False)
    # A.start_monitoring(ordinary_file_key='*/image/*', ToO_file_key='*/image/*_ToO',
    #                    inactivity_period=600, tar=True, protocol='gridftp')
# #%%
# import time
# import os
# import subprocess
# import glob
# import re
# import hashlib
# from tqdm import tqdm
# from astropy.time import Time
# from astropy.table import Table, vstack
# from astropy.io import ascii
# from typing import Optional
# from threading import Thread, Semaphore
# import shutil
# from pathlib import Path
# from datetime import datetime
# from collections import defaultdict
# from tcspy.configuration import mainConfig
# #%%
# class DataTransferManager(mainConfig):
    
#     def __init__(self):
#         super().__init__()
#         self.source_homedir = self.config['TRANSFER_SOURCE_HOMEDIR']
#         self.archive_homedir = self.config['TRANSFER_ARCHIVE_HOMEDIR']
#         self.server_homedir = self.config['TRANSFER_SERVER_HOMEDIR']
#         self.server = self._set_server(**self.config)
#         self.gridftp = self._set_gridftp_params(**self.config)
#         self.process: Optional[subprocess.Popen] = None
#         self.rsync_processes = []
#         self._abort_requested = False 
#         self.is_running = False
#         self.too_last_seen = None
        
#     def start_monitoring(self, ordinary_file_key = '*/image/*', ToO_file_key = '*/image/*_ToO', inactivity_period = 1800, save_hash = True, tar = True, transfer = True, move_and_clean = True, protocol = 'gridftp'):
#         """Monitor files and initiate transfers."""
#         print(f'Monitoring started since {Time.now().isot}')
#         while True:
#             current_time = datetime.now()
            
#             # Check for ordinary file transfer at 8 AM local time
#             if current_time.hour == 12 and current_time.minute == 0:
#                 self.transfer_ordinary_files(ordinary_file_key = ordinary_file_key, tar = tar, protocol = protocol)

#             # Check for ToO file transfer based on inactivity (no new files for 30 minutes)
#             self.transfer_ToO_files(inactivity_period = inactivity_period, ToO_file_key = ToO_file_key, save_hash= save_hash, tar = tar, transfer = transfer, move_and_clean = move_and_clean, protocol = protocol)

#             # Sleep for a minute before checking again
#             time.sleep(60)

#     def transfer_ordinary_files(self, ordinary_file_key = '*/image/*', save_hash = True, tar = True, sync_log = True, transfer = True, move_and_clean = True, protocol = 'gridftp'):
#         """Transfer ordinary files at 8 AM."""
#         # Transfer all files with ordinary criteria
#         print(f"Ordinary file transfer triggered at {Time.now().isot}")
#         folder_list = set([os.path.basename(folder) for folder in (glob.glob(os.path.join(self.source_homedir, ordinary_file_key)))])
#         if len(folder_list) > 0:
#             print(f"Transferring ordinary files at {Time.now().isot}")
#             for folder in folder_list:
#                 key = os.path.join(os.path.dirname(ordinary_file_key), folder)
#                 print('Transferring folder:', key)
#                 self.run(key = key, save_hash = save_hash, tar = tar, sync_log = sync_log, transfer = True, move_and_clean = True, protocol = protocol)
        
#     def transfer_ToO_files(self, inactivity_period, ToO_file_key = '*/image/*_ToO', save_hash = True, tar = True, transfer = True, move_and_clean = True, protocol = 'gridftp'):
#         """Transfer ToO files after 30 minutes of inactivity."""
#         too_files = glob.glob(os.path.join(self.source_homedir, ToO_file_key, '*'))
#         folder_list = set([os.path.basename(os.path.dirname(file_)) for file_ in too_files])
#         if too_files:
#             print("ToO files found. Waiting for inactivity...")
#             latest_file_time = max([os.path.getmtime(file_) for file_ in too_files])

#             if self.too_last_seen is None or latest_file_time > self.too_last_seen:
#                 self.too_last_seen = latest_file_time

#             if time.time() - self.too_last_seen >= inactivity_period:
#                 print(f'Transferring ToO files at {Time.now().isot}')
#                 for folder in folder_list:
#                     key = os.path.join(os.path.dirname(ToO_file_key), folder)
#                     print(f"Transferring ToO folder: {key}")
#                     self.run(key=key, save_hash = save_hash, tar = tar, transfer = transfer, move_and_clean = move_and_clean, protocol = protocol, sync_log = True)
#                     self.too_last_seen = None
        
#     def run(self,
#             key: str = '*/image/20240515',
#             output_file_name: str = None,
#             save_hash: bool = True,
#             tar: bool = True,
#             sync_log: bool = True,
#             transfer: bool = True,
#             move_and_clean: bool = True,
#             protocol: str = 'gridftp',
#             from_archive: bool = False):
#         source_dir = self.source_homedir
#         if from_archive:
#             self.source_homedir = self.archive_homedir
#         if protocol == 'hpnscp':
#             self.hpnscp_transfer(key=key, output_file_name=output_file_name, save_hash=save_hash,
#                                  tar=tar, sync_log=sync_log, transfer=transfer, move_and_clean=move_and_clean)
#         elif protocol == 'rsync':
#             self.rsync_transfer(key=key, output_file_name=output_file_name, save_hash=save_hash,
#                                 tar=tar, sync_log=sync_log, transfer=transfer, move_and_clean=move_and_clean)
#         else:
#             self.gridFTP_transfer(key=key, output_file_name=output_file_name, save_hash=save_hash,
#                                   tar=tar, sync_log=sync_log, transfer=transfer, move_and_clean=move_and_clean)
#         self.source_homedir = source_dir

            
#     def gridFTP_transfer(self,
#                          key : str = '*/image/20240515',
#                          output_file_name : str =  None,
#                          save_hash: bool = True,
#                          tar : bool = True,
#                          sync_log: bool = True,
#                          transfer : bool = True,
#                          move_and_clean : bool = True):
#         self.is_running = True
#         if save_hash:
#             self.generate_and_save_hash(source_file_key=key)
#         if not output_file_name:
#             now_str = Time.now().datetime.strftime('%Y%m%d_%H%M%S')
#             output_file_name = os.path.basename(key)+f'_{now_str}.tar'
#         verbose_command = ''
#         if self.gridftp.verbose:
#             verbose_command = '-vb'
#         if tar:
#             source_path = self.tar(source_file_key= key, output_file_key = f'{os.path.join(self.archive_homedir, output_file_name)}', compress = False, sync_log = sync_log)
#         else:
#             source_path = f'{os.path.join(self.archive_homedir, output_file_name)}'
#         logfile = f'/data2/obsdata/transfer_history/{Time.now().isot}.log'
#         command = f"globus-url-copy {verbose_command} -fast -dbg -p {self.gridftp.numparallel} -rst-retries {self.gridftp.numretries} -rst-interval {self.gridftp.retryinterval} file:{source_path} sshftp://{self.server.username}@{self.server.ip}:{self.server.portnum}{self.server_homedir} > {logfile}"
#         #try:
#         if transfer:
#             print('GRIDFTP PROTOCOL WITH THE COMMAND:',command)
#             self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#             stdout, stderr = self.process.communicate()
#             if self.process.returncode == 0:
#                 print(f"Transfer successful: {stdout.decode()}")
#             else:
#                 raise RuntimeError(f"Error during transfer: {stderr.decode()}")
#         #except:
#         #    self.process = None
#         #    self.is_running = False

#         if move_and_clean:
#             self.move_to_archive_and_cleanup(key, source_path)
#         self.process = None
#         self.is_running = False

#     def hpnscp_transfer(self,
#                         key : str = '*/image/20240503',
#                         output_file_name : str = None,
#                         save_hash: bool = True,
#                         tar : bool = True,
#                         sync_log: bool = True,
#                         transfer : bool = True,
#                         move_and_clean : bool = True
#                         ):
#         self.is_running = True
#         if save_hash:
#             self.generate_and_save_hash(source_file_key=key)
#         if not output_file_name:
#             now_str = Time.now().datetime.strftime('%Y%m%d_%H%M%S')
#             output_file_name = os.path.basename(key)+f'_{now_str}.tar'
#         if tar:
#             source_path = self.tar(source_file_key= key, output_file_key = f'{os.path.join(self.archive_homedir, output_file_name)}', compress = False, sync_log = sync_log)
#         else:
#             source_path = f'{os.path.join(self.archive_homedir, output_file_name)}'
#         command = f"hpnscp -P {self.server.portnum} {source_path} {self.server.username}@{self.server.ip}:{self.server_homedir}"
#         try:
#             if transfer:
#                 print('HPNSSH PROTOCOL WITH THE COMMAND:',command)
#                 self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#                 stdout, stderr = self.process.communicate()
#                 if self.process.returncode == 0:
#                     print(f"Transfer successful: {stdout.decode()}")
#                 else:
#                     raise RuntimeError(f"Error during transfer: {stderr.decode()}")
#         except:
#             self.process = None
#             self.is_running = False
#             return
#         if move_and_clean:
#             self.move_to_archive_and_cleanup(key, source_path)
#         self.process = None
#         self.is_running = False

#     def rsync_transfer(self,
#                        key: str = '*/image/2026-09-06_gain2750',
#                        output_file_name: str = None,
#                        save_hash: bool = True,
#                        tar: bool = False,
#                        sync_log: bool = True,
#                        transfer: bool = True,
#                        move_and_clean: bool = True,
#                        numparallel: int = None,
#                        ssh_bin: str = 'hpnssh',
#                        rsync_timeout: int = 120,
#                        retry_interval: int = 10):
#         """
#         tar 없이 유닛별 디렉터리를 rsync 로 병렬 전송한다.
#         전송 후 개수/바이트 검증이 전체 통과하면 move_and_clean 을 수행.
#         allfiles.hash 는 함께 전송되어 서버측 sha256sum -c 검증에 사용된다.
#         (output_file_name, tar 는 다른 프로토콜과 시그니처 호환을 위한 미사용 인자)
#         """
#         self.is_running = True
#         self._abort_requested = False
#         self.rsync_processes = []
#         try:
#             if numparallel is None:
#                 numparallel = self.gridftp.numparallel

#             # 전송 전 해시 저장 (각 유닛 디렉터리에 allfiles.hash 생성)
#             if save_hash:
#                 self.generate_and_save_hash(source_file_key=key)

#             # key 로 소스 디렉터리들(유닛별) 수집
#             source_pattern = os.path.join(self.source_homedir, key)
#             source_dirs = sorted(glob.glob(source_pattern))
#             if not source_dirs:
#                 print(f"[rsync] No source dirs matched: {source_pattern}")
#                 self.is_running = False
#                 return

#             pattern = re.compile(r'7DT\d{2}')
#             unit_src = {}
#             for source_dir in source_dirs:
#                 if not os.path.isdir(source_dir):
#                     continue
#                 match = pattern.search(source_dir)
#                 if match:
#                     unit_src[match.group()] = source_dir
#                 else:
#                     print(f"[rsync] Could not find telescope name, skipping: {source_dir}")

#             if not unit_src:
#                 print("[rsync] No unit directories to transfer.")
#                 self.is_running = False
#                 return

#             ssh_command = f"{ssh_bin} -p {self.server.portnum}"

#             if transfer:
#                 print(f"[rsync] Transfer started: {len(unit_src)} units, parallel {numparallel}")
#                 semaphore = Semaphore(numparallel)
#                 threads = []

#                 def worker(unit, source_dir):
#                     with semaphore:
#                         if self._abort_requested:
#                             return
#                         self._rsync_send_unit(unit, source_dir, ssh_command,
#                                               rsync_timeout, retry_interval)

#                 for unit, source_dir in sorted(unit_src.items()):
#                     thread = Thread(target=worker, args=(unit, source_dir))
#                     thread.start()
#                     threads.append(thread)
#                 for thread in threads:
#                     thread.join()

#                 if self._abort_requested:
#                     print("[rsync] Aborted by user. Skipping verify/move.")
#                     self.is_running = False
#                     return
#                 print("[rsync] All units transfer round finished")

#             # 전송 후 검증 (개수 + 바이트)
#             all_ok = True
#             total_files = 0
#             total_bytes = 0
#             if transfer:
#                 all_ok, total_files, total_bytes = self._rsync_verify(unit_src, ssh_command)

#             # transfer history 기록 (날짜 1건 = 1줄)
#             if sync_log and transfer:
#                 try:
#                     date_key = os.path.basename(next(iter(unit_src.values())).rstrip('/'))
#                     self._log_rsync_history(date_key, unit_src, total_bytes)
#                 except Exception as e:
#                     print(f"[rsync] Failed to log transfer history: {e}")

#             # 전체 OK 일 때만 이동/정리
#             if move_and_clean:
#                 if all_ok:
#                     print("[rsync] Verification passed -> move to archive and cleanup")
#                     self.move_to_archive_and_cleanup(key, tar_path='/nonexistent_rsync_no_tar')
#                 else:
#                     print("################################################################")
#                     print("## CRITICAL: Mismatched unit(s) found -> skip move, keep source ##")
#                     print("################################################################")

#         finally:
#             self.process = None
#             self.rsync_processes = []
#             self.is_running = False
            
#     def abort(self):
#         # rsync 병렬 전송 중이면 모든 하위 rsync 프로세스를 종료
#         self._abort_requested = True
#         if getattr(self, 'rsync_processes', None):
#             for p in list(self.rsync_processes):
#                 try:
#                     if p.poll() is None:
#                         p.terminate()
#                         try:
#                             p.wait(timeout=5)
#                         except subprocess.TimeoutExpired:
#                             p.kill()
#                 except Exception as e:
#                     print(f"Error terminating rsync process: {e}")
#             self.rsync_processes = []
#             print("Rsync transfer(s) terminated successfully.")

#         # 기존 단일 프로세스(gridftp/hpnscp/tar) 종료 (원본 동작 유지)
#         if self.process and self.process.poll() is None:
#             self.process.terminate()
#             try:
#                 self.process.wait(timeout=5)
#                 print("Transfer terminated successfully.")
#             except subprocess.TimeoutExpired:
#                 self.process.kill()
#                 print("Transfer forcefully killed after timeout.")
#             finally:
#                 self.process = None
#         elif not getattr(self, 'rsync_processes', None):
#             print("No running transfer to terminate.")
            

#     def generate_and_save_hash(self, source_file_key: str) -> None:
#         """
#         Generates SHA-256 hashes for all files matching the given pattern
#         and saves each hash as a separate file in the same directory.

#         Parameters:
#         source_file_key (str): Glob pattern to match source files (e.g., '7DT/*.fits').

#         Returns:
#         None
#         """
#         try:
#             # Match all files using the provided pattern
#             source_keys = os.path.join(self.source_homedir, source_file_key, '*')
#             file_paths = glob.glob(source_keys)
#             if not file_paths:
#                 raise ValueError(f"No files matched the pattern: {source_file_key}")

#             telescope_path_dict = defaultdict(list)  # Initialize a dictionary with lists as default values
#             pattern = r'7DT\d{2}'  # Regex to match telescope names like 7DT12, 7DT01

#             # Divide the files into lists based on the telescope name
#             for path in file_paths:
#                 if os.path.isfile(path):  # Ensure it's a file, not a directory
#                     match = re.search(pattern, path)
#                     if match:
#                         telescope_name = match.group()
#                         telescope_path_dict[telescope_name].append(path)

#             for tel_name, file_paths in telescope_path_dict.items():
#                 hashlist = []
#                 filenamelist = []
#                 for file_path in tqdm(file_paths, desc=f'Generating hashes of {tel_name} files...'):
#                     hasher = hashlib.sha256()
#                     with open(file_path, 'rb') as file:
#                         # Read the file in chunks to handle large files efficiently
#                         for chunk in iter(lambda: file.read(4096), b""):
#                             hasher.update(chunk)

#                     # Generate the hash
#                     file_hash = hasher.hexdigest()
#                     hashlist.append(file_hash)
#                     filenamelist.append(os.path.basename(file_path))

#                 # Save the hash to a file in the telescope directory
#                 tel_directory = os.path.dirname(file_paths[0])  # Get the directory of the first file for this telescope
#                 hash_file_path = os.path.join(tel_directory, 'allfiles.hash')
#                 with open(hash_file_path, 'w') as hash_file:
#                     for hash_, filename in zip(hashlist, filenamelist):
#                         hash_file.write(f"{hash_} {filename}\n")
#                 print(f"Hash generated and saved for: {tel_name} -> {hash_file_path}")

#         except Exception as e:
#             raise RuntimeError(f"An error occurred while generating and saving hashes: {str(e)}")

#     def tar(self,
#             source_file_key: str,
#             output_file_key: str,
#             compress: bool = False,
#             sync_log: bool = True):
#         compress_command = '-cvf'
#         if compress:
#             compress_command = '-cvjf'

#         command = f'cd {self.source_homedir} && tar {compress_command} {output_file_key} -C {self.source_homedir} {source_file_key}'

#         try:
#             print(f"Tarball started: {Time.now().isot}")
#             self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#             stdout, stderr = self.process.communicate()
#             if self.process.returncode == 0:
#                 print(f"Tarball successful: {stdout.decode()}")
#             else:
#                 print(f"Error during Tarball: {stderr.decode()}")
#                 return  # stop if tar fails
#         except subprocess.CalledProcessError as e:
#             print(f"Error during Tarball: {e.stderr.decode()}")
#             return
#         finally:
#             self.process = None

#         if sync_log:
#             try:
#                 tar_full_path = os.path.abspath(output_file_key)
#                 tar_size = os.path.getsize(tar_full_path)
#                 timestamp = Time.now()
#                 time_str = timestamp.strftime('%Y%m%d%H%M%S')
#                 iso_time = timestamp.isot
#                 log_folder = self.config['TRANSFER_SYNCFOLDER']
#                 log_file = os.path.join(log_folder, 'transfer_history.ascii_fixed_width')

#                 # 1. Create filelist
#                 filelist_filename = f"{time_str}.filelist"
#                 filelist_path = os.path.join(log_folder, filelist_filename)
                
#                 list_command = f"tar -tf {tar_full_path}"
#                 result = subprocess.run(list_command, shell=True, capture_output=True, text=True)

#                 # Extract only basenames (ignore directory paths)
#                 filelist = [
#                     os.path.basename(line.strip())
#                     for line in result.stdout.strip().split('\n')
#                     if line.strip()  # skip empty lines
#                 ]

#                 # Save to file
#                 with open(filelist_path, 'w') as flist:
#                     flist.write('\n'.join(filelist) + '\n')

#                 # 2. Check existing log
#                 if os.path.exists(log_file):
#                     sync_history = ascii.read(log_file, format='fixed_width')
#                     existing_names = sync_history['Filename'].tolist()
#                 else:
#                     sync_history = Table(names=['Filename', 'Size', 'Time', 'File_folder'],
#                                         dtype=['str', 'str', 'str', 'str'])
#                     existing_names = []

#                 # 3. Append if not already in log
#                 basename = os.path.basename(tar_full_path)
#                 if basename not in existing_names:
#                     new_row = Table(
#                         [[basename], [f"{tar_size} bytes"], [iso_time], [filelist_filename]],
#                         names=['Filename', 'Size', 'Time', 'File_folder']
#                     )
#                     updated_table = vstack([sync_history, new_row])
#                     ascii.write(updated_table, log_file, format='fixed_width', overwrite=True)
#                     print(f"Tar file info logged at: {log_file}")
#                     print(f"File list saved at: {filelist_path}")
#                 else:
#                     print(f"{basename} already exists in log. Skipping log update.")
#             except Exception as e:
#                 print(f"Failed to log tar file info or save file list: {e}")
#         return output_file_key
                        
#     def move_to_archive_and_cleanup(self, key, tar_path):
#         source_pattern = os.path.join(self.source_homedir, key)
#         source_dirs = glob.glob(source_pattern)

#         for source_dir in tqdm(source_dirs, desc='Moving folders...'):
#             source_dir = Path(source_dir)

#             match = re.findall(r'7DT\d+', str(source_dir))
#             if not match:
#                 print(f"Could not find telescope name in path: {source_dir}")
#                 continue

#             parent_dir = match[0]
#             archive_parent = Path(self.archive_homedir) / parent_dir
#             destination_dir = archive_parent / source_dir.name

#             archive_parent.mkdir(parents=True, exist_ok=True)

#             try:
#                 if not destination_dir.exists():
#                     shutil.move(str(source_dir), str(destination_dir))
#                     print(f"Moved folder: {source_dir} -> {destination_dir}")

#                 else:
#                     print(f"Destination exists. Moving files into: {destination_dir}")

#                     for item in source_dir.iterdir():
#                         target = destination_dir / item.name

#                         if target.exists():
#                             print(f"Skipping existing item: {target}")
#                             continue

#                         shutil.move(str(item), str(target))

#                     # Remove the source folder after moving/skipping contents
#                     shutil.rmtree(source_dir)
#                     print(f"Removed source folder: {source_dir}")

#             except Exception as e:
#                 print(f"Error during move: {e}")

#         try:
#             os.remove(tar_path)
#             print(f"Removed tar file: {tar_path}")
#         except Exception as e:
#             print(f"Error removing tar file: {e}")

#     def _rsync_send_unit(self, unit, source_dir, ssh_command, rsync_timeout, retry_interval):
#         """한 유닛 디렉터리를 rsync 로 전송한다. 순단 시 --append 로 자동 이어받기 재시도."""
#         source_path = source_dir.rstrip('/')  # 끝 슬래시 없음 -> 목적지에 말단 폴더째 생성
#         rel_parent, _leaf = self._rel_parent_and_leaf(source_path)  # image 유무 자동
#         rel_parent_slash = (rel_parent + '/') if rel_parent else ''
#         destination = (f"{self.server.username}@{self.server.ip}:"
#                        f"{self.server_homedir.rstrip('/')}/{rel_parent_slash}")

#         # 목적지 상위 디렉터리 보장
#         mkdir_command = (f"{ssh_command} {self.server.username}@{self.server.ip} "
#                          f"'mkdir -p {self.server_homedir.rstrip('/')}/{rel_parent_slash}'")
#         subprocess.run(mkdir_command, shell=True,
#                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

#         command = (f"rsync -a --partial --inplace --append "
#                    f"--timeout={rsync_timeout} "
#                    f"-e '{ssh_command}' '{source_path}' '{destination}'")
#         max_retries = getattr(self.gridftp, 'numretries', 60) or 60
#         fatal_codes = {1, 2, 3, 4}  # syntax/protocol/file-select/requested-action = 재시도 무의미
#         tries = 0
#         while True:
#             if self._abort_requested:
#                 print(f"[rsync] {unit} aborted")
#                 return
#             process = subprocess.Popen(command, shell=True)
#             self.rsync_processes.append(process)
#             process.wait()
#             try:
#                 self.rsync_processes.remove(process)
#             except ValueError:
#                 pass

#             if self._abort_requested:
#                 print(f"[rsync] {unit} aborted")
#                 return
#             if process.returncode == 0:
#                 print(f"[rsync] {unit} done")
#                 return
#             if process.returncode in fatal_codes:
#                 print(f"[rsync] {unit} fatal error (rc={process.returncode}) - not retrying")
#                 return
#             tries += 1
#             if tries > max_retries:
#                 print(f"[rsync] {unit} exceeded {max_retries} retries - giving up "
#                       f"(will be caught as mismatch in verify)")
#                 return
#             print(f"[rsync] {unit} interrupted (rc={process.returncode}, retry {tries}/{max_retries}), "
#                   f"restart in {retry_interval}s")
#             time.sleep(retry_interval)

#     def _rel_parent_and_leaf(self, source_dir: str):
#         """
#         소스 절대경로에서 "유닛(7DT??) 이후의 상대경로 부모" 와 "말단 폴더명" 을 뽑는다.
#         image 유무(일반 전송 / 아카이브 재전송)에 상관없이 소스 구조를 서버에 재현하기 위함.
#           .../7DT01/image/2026-09-06_gain2750 -> ('7DT01/image', '2026-09-06_gain2750')
#           .../7DT01/2026-09-06_gain2750       -> ('7DT01',       '2026-09-06_gain2750')
#         유닛명을 못 찾으면 ('', basename) 반환.
#         """
#         source_path = source_dir.rstrip('/')
#         parts = source_path.split(os.sep)
#         unit_idx = None
#         for j in range(len(parts) - 1, -1, -1):
#             if re.fullmatch(r'7DT\d{2}', parts[j]):
#                 unit_idx = j
#                 break
#         if unit_idx is None:
#             return '', os.path.basename(source_path)
#         rel_parts = parts[unit_idx:]
#         leaf = rel_parts[-1]
#         rel_parent = '/'.join(rel_parts[:-1])
#         return rel_parent, leaf

#     def _rsync_verify(self, unit_src: dict, ssh_command: str):
#         """
#         소스(로컬) vs 서버(원격) 의 유닛별 (파일개수, 총바이트) 비교.
#         반환: (all_ok: bool, total_source_files: int, total_source_bytes: int)
#         """
#         all_ok = True
#         total_count = 0
#         total_bytes = 0
#         print(f"{'UNIT':8} | {'SRC#':>7} {'SRC_BYTES':>14} | "
#               f"{'DST#':>7} {'DST_BYTES':>14} | OK?")
#         print("-" * 72)
#         for unit, source_dir in sorted(unit_src.items()):
#             source_count, source_bytes = 0, 0
#             for root, _, files in os.walk(source_dir):
#                 for filename in files:
#                     filepath = os.path.join(root, filename)
#                     try:
#                         source_bytes += os.path.getsize(filepath)
#                         source_count += 1
#                     except OSError:
#                         pass
#             total_count += source_count
#             total_bytes += source_bytes

#             # 전송과 동일한 상대경로 규칙으로 원격 경로 계산 (image 유무 자동)
#             rel_parent, leaf = self._rel_parent_and_leaf(source_dir)
#             rel = f"{rel_parent}/{leaf}" if rel_parent else leaf
#             remote_dir = f"{self.server_homedir.rstrip('/')}/{rel}"
#             remote_command = (
#                 f"{ssh_command} {self.server.username}@{self.server.ip} "
#                 f"\"find '{remote_dir}' -type f 2>/dev/null | wc -l; "
#                 f"find '{remote_dir}' -type f -printf '%s\\n' 2>/dev/null "
#                 f"| awk '{{t+=\\$1}} END{{print t+0}}'\""
#             )
#             try:
#                 output = subprocess.run(remote_command, shell=True, capture_output=True,
#                                         text=True, timeout=120).stdout.split()
#                 dest_count = int(output[0]) if len(output) > 0 else 0
#                 dest_bytes = int(output[1]) if len(output) > 1 else 0
#             except Exception as e:
#                 print(f"[rsync] {unit} remote query failed: {e}")
#                 dest_count, dest_bytes = -1, -1

#             ok = (source_count == dest_count and source_bytes == dest_bytes)
#             if not ok:
#                 all_ok = False
#             print(f"{unit:8} | {source_count:7d} {source_bytes:14d} | "
#                   f"{dest_count:7d} {dest_bytes:14d} | {'OK' if ok else '!! MISMATCH'}")
#         print("-" * 72)
#         print("=> All units matched" if all_ok else "=> Mismatched unit(s) found")
#         return all_ok, total_count, total_bytes

#     def _log_rsync_history(self, date_key: str, unit_src: dict, total_bytes: int):
#         """
#         rsync 전송 1건(날짜 1개)을 기존 transfer_history 에 1줄로 이어쓴다.
#         스키마 그대로: Filename / Size / Time / File_folder
#           - Filename    : 날짜 키 (예: 2026-09-06_gain2750)  [tar 파일명 대체]
#           - Size        : '<총바이트> bytes'
#           - Time        : ISO 시각
#           - File_folder : <time_str>.filelist  (내용물 전체 목록 별도 저장)
#         """
#         timestamp = Time.now()
#         time_str = timestamp.strftime('%Y%m%d%H%M%S')
#         iso_time = timestamp.isot
#         log_folder = self.config['TRANSFER_SYNCFOLDER']
#         log_file = os.path.join(log_folder, 'transfer_history.ascii_fixed_width')

#         # 1) filelist 저장 (모든 유닛의 파일, 유닛명 접두)
#         filelist_filename = f"{time_str}.filelist"
#         filelist_path = os.path.join(log_folder, filelist_filename)
#         filelist = []
#         for unit, source_dir in sorted(unit_src.items()):
#             for root, _, files in os.walk(source_dir):
#                 for filename in files:
#                     filelist.append(f"{unit}/{filename}")
#         with open(filelist_path, 'w') as flist:
#             flist.write('\n'.join(filelist) + '\n')

#         # 2) 기존 로그 읽기
#         if os.path.exists(log_file):
#             sync_history = ascii.read(log_file, format='fixed_width')
#             existing_names = sync_history['Filename'].tolist()
#         else:
#             sync_history = Table(names=['Filename', 'Size', 'Time', 'File_folder'],
#                                  dtype=['str', 'str', 'str', 'str'])
#             existing_names = []

#         # 3) 같은 날짜키가 없으면 추가
#         if date_key not in existing_names:
#             new_row = Table(
#                 [[date_key], [f"{total_bytes} bytes"], [iso_time], [filelist_filename]],
#                 names=['Filename', 'Size', 'Time', 'File_folder']
#             )
#             updated_table = vstack([sync_history, new_row])
#             ascii.write(updated_table, log_file, format='fixed_width', overwrite=True)
#             print(f"Transfer info logged at: {log_file}")
#             print(f"File list saved at: {filelist_path}")
#         else:
#             print(f"{date_key} already exists in log. Skipping log update.")

#     def _set_server(self,
#                     TRANSFER_SERVER_IP,
#                     TRANSFER_SERVER_USERNAME,
#                     TRANSFER_SERVER_PORTNUM,
#                     **kwrags
#                     ):    
#         class server: 
#             ip = TRANSFER_SERVER_IP
#             username = TRANSFER_SERVER_USERNAME
#             portnum = TRANSFER_SERVER_PORTNUM
#             def __repr__(self): 
#                 return ('SERVER CONFIGURATION ============\n'
#                         f'server.ip = {self.ip}\n'
#                         f'server.username = {self.username}\n'
#                         f'server.portnum = {self.portnum}\n' 
#                         '=================================')
#         return server()
        
#     def _set_gridftp_params(self,
#                             TRANSFER_GRIDFTP_NUMPARALLEL : int = 64, # Number of parallel data connection
#                             TRANSFER_GRIPFTP_VERBOSE : bool = True, # Verbose?
#                             TRANSFER_GRIDFTP_RETRIES : int = 10, # Number of retries
#                             TRANSFER_GRIDFTP_RTINTERVAL : int = 60, # Interval in seconds before retry                           
#                             **kwrags
#                             ):
#         class gridftp: 
#             numparallel = TRANSFER_GRIDFTP_NUMPARALLEL
#             verbose = TRANSFER_GRIPFTP_VERBOSE
#             numretries = TRANSFER_GRIDFTP_RETRIES
#             retryinterval = TRANSFER_GRIDFTP_RTINTERVAL
#             def __repr__(self): 
#                 return ('GRIDFTP CONFIGURATION ============\n'
#                         f'gridftp.numparallel = {self.numparallel}\n'
#                         f'gridftp.verbose = {self.verbose}\n'
#                         f'gridftp.numretries = {self.numretries}\n'
#                         f'gridftp.retryinterval = {self.retryinterval}\n' 
#                         '=================================')
#         return gridftp()


        
    
# #%%
# if __name__ == '__main__':
#     A = DataTransferManager()
#     import time

#     # A.run(key = '*/image/2026-09-06_gain2750', save_hash = True, tar = True,
#     #       sync_log = True, transfer = True, move_and_clean = False,
#     #       from_archive = False)
#     # A.run(key = '*/image/2026-03-14_gain2750', save_hash = True, tar = True,
#     #       sync_log = True, transfer = True, move_and_clean = True,
#     #       from_archive = False)
#     # A.run(key = '*/image/2025-07-08_gain2750', save_hash = True, tar = True,
#     #       sync_log = True, transfer = True, move_and_clean = True,
#     #       from_archive = False)
#     # time.sleep(600)
#     # A.run(key = '*/image/2025-05-23_gain2750', save_hash = True, tar = True,
#     #       sync_log = True, transfer = True, move_and_clean = True,
#     #       from_archive = False)
#     # A.run(key = '*/2025-03-23_gain2750', save_hash = True, tar = True,
#     #       sync_log = True, transfer = True, move_and_clean = False,
#     #       from_archive = True)
#     # A.run(key = '*/2025-12-23_gain2750', save_hash = True, tar = True,
#     #       sync_log = True, transfer = True, move_and_clean = False,
#     #       from_archive = True)
#     # A.run(key = '*/2025-04-03_gain0', save_hash = True, tar = True,
#     #       sync_log = True, transfer = True, move_and_clean = False,
#     #       from_archive = True)
#     # A.run(key = '*/2025-11-21_gain2750', save_hash = True, tar = True,
#     #       sync_log = False, transfer = False, move_and_clean = False,
#     #       from_archive = True)
#     #A.move_to_archive_and_cleanup(key = '*/image/2024-10-24_gain2750', tar_path = '/data1/obsdata_archive/2024-10-25_gain2750.tar')
#     # A.start_monitoring(
#     #     ordinary_file_key='*/image/*',   # Adjust these parameters as needed
#     #     ToO_file_key='*/image/*_ToO',
#     #     inactivity_period=600,             # 30 minutes of inactivity
#     #     tar=True,                        # Compress files into tar
#     #     protocol='gridftp'               # File transfer protocol
#     # )

# # # # %%

# # %%
