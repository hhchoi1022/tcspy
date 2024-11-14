#%%
from multiprocessing import Event
from multiprocessing import Manager
from astropy.time import Time
import astropy.units as u
import time

from tcspy.devices import SingleTelescope
from tcspy.devices import TelescopeStatus
from tcspy.interfaces import *
from tcspy.utils.error import *
from tcspy.utils.logger import mainLogger
from tcspy.utils.target import SingleTarget
from tcspy.utils.exception import *

from tcspy.action.level1 import SlewRADec
from tcspy.action.level1 import SlewAltAz
from tcspy.action.level1 import Exposure
from tcspy.action.level1 import ChangeFocus
from tcspy.action.level1 import ChangeFilter
from tcspy.action.level2 import AutoFocus

#%%
class SingleObservation(Interface_Runnable, Interface_Abortable):
    """
    A class representing a single observation action for a single telescope.

    Parameters
    ----------
    singletelescope : SingleTelescope
        An instance of SingleTelescope class representing the individual telescope on which the single observation action is performed.
    abort_action : Event
        An instance of the built-in Event class to handle the abort action.

    Methods
    -------
    run(exptime, count, filter_=None, binning='1', imgtype='Light', ra=None, dec=None, alt=None, az=None, name=None,
        obsmode='Single', specmode=None, ntelescope=1, objtype=None, autofocus_before_start=False,
        autofocus_when_filterchange=False, **kwargs)
        Triggers the single observation process. This includes checking device status, setting target, slewing,
        changing filter and focuser position according to the necessity and conducting exposure.
    abort()
        Aborts any running actions related to the filter wheel, camera, and mount.
    """
    
    def __init__(self, 
                 singletelescope : SingleTelescope,
                 abort_action : Event):
        self.telescope = singletelescope
        self.telescope_status = TelescopeStatus(self.telescope)
        self.abort_action = abort_action
        self.shared_memory_manager = Manager()
        self.shared_memory = self.shared_memory_manager.dict()
        self.shared_memory['succeeded'] = False
        self.shared_memory['status'] = dict()
        self._log = mainLogger(unitnum = self.telescope.unitnum, logger_name = __name__+str(self.telescope.unitnum)).log()
        self.is_running = False

    def run(self, 
            # Exposure information
            exptime : str,
            count : str,
            obsmode : str = 'Single',
            filter_ : str = None,
            specmode : str = None,
            ntelescope : int = 1,
            gain : int = 2750,
            binning : str = '1',
            imgtype : str = 'Light',
            
            # Target information
            ra : float = None, # When radec == None: do not move 
            dec : float = None,
            alt : float = None, # When altaz == None: do not move 
            az : float = None,
            name : str = None,
            objtype : str = None,
            id_: str = None,
            note : str = None,
            comment : str = None,
            is_ToO : bool = False,
            
            # Auxiliary parameters
            force_slewing : bool = False,
            autofocus_use_history : bool = True,
            autofocus_history_duration : float = 60,
            autofocus_before_start : bool = False,
            autofocus_when_filterchange : bool = False,
            autofocus_when_elapsed : bool = False,
            autofocus_elapsed_duration : float = 60,
            observation_status : dict = None,
            **kwargs
            ):
        """
        Triggers the single observation process. This includes checking device status, setting target, slewing,
        changing filter and focuser position according to the necessity and conducting exposure.

        Parameters
        ----------
        exptime : str
            The exposure time.
        count : str
            The exposure count.
        filter_ : str, optional
            The type of filter to be used. 
        binning : str, optional
            The binning value. If not provided, defaults to '1'.
        imgtype : str, optional
            The type of image. If not provided, defaults to 'Light'.
        ra : float, optional
            The right ascension of the target. If not provided, the telescope does not move.
        dec : float, optional
            The declination of the target. If not provided, the telescope does not move.
        alt : float, optional
            The altitude of the target. If neither `alt` nor `az` are provided, the telescope does not move.
        az : float, optional
            The azimuth of the target. If neither `alt` nor `az` are provided, the telescope does not move.
        autofocus_before_start : bool, optional
            Whether or not to autofocus before beginning the first observation set. If not provided, it will not autofocus before beginning the observation.
        autofocus_when_filterchange : bool, optional
            Whether or not to autofocus when filter changes. If not provided, it will not autofocus when the filter changes.
        
        Raises
        ------
        ConnectionException:
            If the required devices are disconnected.
        AbortionException:
            If the action is aborted during execution.
        ActionFailedException:
            If the slewing process or the exposure fails.
        """
        
        """
          exptime = '5,5'
          count = '2,2'
          filter_ = 'm400,m425'
          binning = '1'
          imgtype = 'Light'
          ra = 200
          dec = -58.0666 
          obsmode = 'Spec'
          autofocus_use_history = True
          autofocus_history_duration = 60
          autofocus_before_start = True
          autofocus_when_filterchange= True
          autofocus_when_elapsed = True
          autofocus_elapsed_duration = 60
          observation_status = None
          az = None
          alt = None
          name = None
          objtype = None
          specmode = None
          ntelescope = 1
          id_ = '193yhiujashdijqhweu9'
          force_slewing = False
          note = 'This is for Deep observing mode. (5 Telescopes will be used for sequential g,r,i observation)'
        """        
        self._log.info(f'==========LV2[{type(self).__name__}] is triggered.')
        self.is_running = True
        self.shared_memory['succeeded'] = False
        # Check condition of the instruments for this Action
        self._log.info(f'Debugging point 0.1')
        trigger_abort_disconnected = False
        try:        
            status_mount = self.telescope_status.mount
        except:
            trigger_abort_disconnected = True
            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: mount status cannot be loaded.')
        self._log.info(f'Debugging point 0.4')
        try:
            status_camera = self.telescope_status.camera
        except:
            trigger_abort_disconnected = True
            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: camera status cannot be loaded.')
        self._log.info(f'Debugging point 0.3')
        try:
            status_filterwheel = self.telescope_status.filterwheel
        except:
            trigger_abort_disconnected = True
            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: filterwheel status cannot be loaded.')
        self._log.info(f'Debugging point 0.2')

        if status_camera.lower() == 'disconnected':
            trigger_abort_disconnected = True
            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: camera is disconnected.')
        if status_filterwheel.lower() == 'disconnected':
            trigger_abort_disconnected = True
            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: filterwheel is disconnected.')
        if status_mount.lower() == 'disconnected':
            trigger_abort_disconnected = True
            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: mount is disconnected.')
        if trigger_abort_disconnected:
            self.is_running = False
            raise ConnectionException(f'==========LV2[{type(self).__name__}] is failed: devices are disconnected.')
        # Done
        self._log.info(f'Debugging point 1')

        
        # Set target
        target = SingleTarget(observer = self.telescope.observer, 
                              ra = ra, 
                              dec = dec, 
                              alt = alt, 
                              az = az, 
                              name = name, 
                              objtype= objtype,
                              id_ = id_,
                              note = note,
                              comment = comment,
                              is_ToO = is_ToO,
                              
                              exptime = exptime,
                              count = count,
                              filter_ = filter_,
                              binning = binning, 
                              gain = gain,
                              obsmode = obsmode,
                              specmode = specmode,
                              ntelescope = ntelescope
                              )
        target_info = target.target_info
        exposure_info = target.exposure_info
        self._log.info(f'Debugging point 2')

        if exposure_info['filter_'] == 'None':
            try:
                exposure_info['filter_'] = exposure_info['specmode_filter'][self.telescope.tel_name]
            except:
                self.is_running = False
                self._log.critical(f'==========LV2[{type(self).__name__}] is failed: filter is not defined.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: filter is not defined.')
        self._log.info(f'Debugging point 3')

        # Slewing
        if target.status['coordtype'] == 'radec':
            try:
                slew = SlewRADec(singletelescope = self.telescope, abort_action= self.abort_action)
                result_slew = slew.run(ra = float(target_info['ra']), dec = float(target_info['dec']), force_action = force_slewing)
            except ConnectionException:
                self.is_running = False
                self._log.critical(f'==========LV2[{type(self).__name__}] is failed: telescope is disconnected.')
                raise ConnectionException(f'[{type(self).__name__}] is failed: telescope is disconnected.')
            except AbortionException:
                self.abort()
            except ActionFailedException:
                self.is_running = False
                self._log.critical(f'==========LV2[{type(self).__name__}] is failed: slewing failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: slewing failure.')

        elif target.status['coordtype'] == 'altaz':
            try:
                slew = SlewAltAz(singletelescope = self.telescope, abort_action= self.abort_action)
                result_slew = slew.run(alt = float(target_info['alt']), az = float(target_info['az']), force_action = force_slewing)
            except ConnectionException:
                self.is_running = False
                self._log.critical(f'==========LV2[{type(self).__name__}] is failed: telescope is disconnected.')
                raise ConnectionException(f'[{type(self).__name__}] is failed: telescope is disconnected.')
            except AbortionException:
                self.abort()
            except ActionFailedException:
                self.is_running = False
                self._log.critical(f'==========LV2[{type(self).__name__}] is failed: slewing failure.')
                raise ActionFailedException(f'[{type(self).__name__}] is failed: slewing failure.')
        else:
            self.is_running = False
            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: Coordinate type of the target : {target.status["coordtype"]} is not defined')
            raise ActionFailedException(f'[{type(self).__name__}] is failed: Coordinate type of the target : {target.status["coordtype"]} is not defined')
        self._log.info(f'Debugging point 4')

        # Get exposure information
        observation_requested = self._exposureinfo_to_list(filter_ = exposure_info['filter_'], exptime = exposure_info['exptime'], count = exposure_info['count'], binning = exposure_info['binning'])
        # Set observation status. If observation_status is inputted, run() will resume according to the observation_status
        if not observation_status:
            observation_status = self._set_observation_status(filter_ = exposure_info['filter_'], exptime = exposure_info['exptime'], count = exposure_info['count'], binning = exposure_info['binning'])
        
        # When inputted observation_status.keys() are not matched with observation_requested, set default value
        if not (set(observation_status.keys())) == (set(observation_requested['filter_'])):
            observation_status = self._set_observation_status(filter_ = exposure_info['filter_'], exptime = exposure_info['exptime'], count = exposure_info['count'], binning = exposure_info['binning'])
        
        action_autofocus = AutoFocus(singletelescope= self.telescope, abort_action= self.abort_action)
        self.shared_memory['status'] = observation_status
        self._log.info(f'Debugging point 5')

        observation_trigger = {'filter_': [],
                               'exptime': [],
                               'count': [],
                               'binning': []}
        
        for filter_, exptime, count, binning in zip(observation_requested['filter_'], observation_requested['exptime'], observation_requested['count'], observation_requested['binning']):
             observation_status_filter = observation_status[filter_]
             net_count = observation_status_filter['triggered'] - observation_status_filter['observed']
             if net_count > 0:
                observation_trigger['filter_'].append(filter_)
                observation_trigger['exptime'].append(exptime)
                observation_trigger['count'].append(net_count)
                observation_trigger['binning'].append(binning)
        self._log.info(f'Debugging point 6')
 
        # Autofocus before beginning the first observation set 
        if autofocus_before_start:
            try:
                filter_ = observation_trigger['filter_'][0]
                result_autofocus = action_autofocus.run(filter_ = filter_, use_offset = True, use_history= autofocus_use_history, history_duration = autofocus_history_duration)
            except ConnectionException:
                self.is_running = False
                self._log.critical(f'==========LV2[{type(self).__name__}] is failed: Device connection is lost.')
                raise ConnectionException(f'[{type(self).__name__}] is failed: Device connection is lost.')
            except AbortionException:
                self.abort()
            except ActionFailedException:
                self._log.warning(f'[{type(self).__name__}] Autofocus is failed. Return to the previous focus value')
                pass
        self._log.info(f'Debugging point 7')
        result_all_exposure = []
        for filter_, exptime, count, binning in zip(observation_trigger['filter_'], observation_trigger['exptime'], observation_trigger['count'], observation_trigger['binning']):
            info_filterwheel = self.telescope.filterwheel.get_status()
            current_filter = info_filterwheel['filter']
            is_filter_changed = (current_filter != filter_)
            
            if is_filter_changed:
                self._log.info(f'Debugging point 8')

                # Apply offset
                offset = self.telescope.filterwheel.get_offset_from_currentfilt(filter_ = filter_)
                self._log.info(f'[{type(self).__name__}] Focuser is moving with the offset of {offset}[{current_filter} >>> {filter_}]')
                try:
                    result_focus = ChangeFocus(singletelescope = self.telescope, abort_action = self.abort_action).run(position = offset, is_relative= True)
                except ConnectionException:
                    self.is_running = False
                    self._log.critical(f'==========LV2[{type(self).__name__}] is failed: Focuser is disconnected.')                
                    raise ConnectionException(f'[{type(self).__name__}] is failed: Focuser is disconnected.')                
                except AbortionException:
                    self.abort()
                except ActionFailedException:
                    self.is_running = False
                    self._log.critical(f'==========LV2[{type(self).__name__}] is failed: Focuser movement failure.')
                    raise ActionFailedException(f'[{type(self).__name__}] is failed: Focuser movement failure.')
                
                # Filterchange
                try:    
                    result_filterchange = ChangeFilter(singletelescope= self.telescope, abort_action= self.abort_action).run(filter_ = filter_)
                except ConnectionException:
                    self.is_running = False
                    self._log.critical(f'==========LV2[{type(self).__name__}] is failed: Filterwheel is disconnected.')                
                    raise ConnectionException(f'[{type(self).__name__}] is failed: Filterwheel is disconnected.')                
                except AbortionException:
                    self.abort()
                except ActionFailedException:
                    self.is_running = False
                    self._log.critical(f'==========LV2[{type(self).__name__}] is failed: Filterwheel movement failure.')
                    raise ActionFailedException(f'[{type(self).__name__}] is failed: Filterwheel movement failure.')

                # Autofocus when filter changed
                if autofocus_when_filterchange:
                    try:
                        result_autofocus = action_autofocus.run(filter_ = filter_, use_offset = False, use_history= autofocus_use_history, history_duration= autofocus_history_duration)
                    except ConnectionException:
                        self.is_running = False
                        self._log.critical(f'==========LV2[{type(self).__name__}] is failed: Device connection is lost.')
                        raise ConnectionException(f'[{type(self).__name__}] is failed: Device connection is lost.')
                    except AbortionException:
                        self.abort()
                    except ActionFailedException:
                        self._log.warning(f'[{type(self).__name__}] Autofocus is failed. Return to the previous focus value')
                        pass
            self._log.info(f'Debugging point 9')
            # Exposure
            action_exposure = Exposure(singletelescope = self.telescope, abort_action = self.abort_action)
            for frame_number in range(int(count)):
                
                # Autofocus_when_elapsed
                if autofocus_when_elapsed:
                    history = action_autofocus.history[filter_]
                    now = Time.now()
                    if ((Time(history['update_time']) + autofocus_elapsed_duration * u.minute) < now) | (not history['succeeded']):
                        try:
                            result_autofocus = action_autofocus.run(filter_ = filter_, use_offset = False, use_history = False)
                        except ConnectionException:
                            self.is_running = False
                            self._log.critical(f'==========LV2[{type(self).__name__}] is failed: Device connection is lost.')
                            raise ConnectionException(f'[{type(self).__name__}] is failed: Device connection is lost.')
                        except AbortionException:
                            self.abort()
                        except ActionFailedException:
                            self._log.warning(f'[{type(self).__name__}] Autofocus is failed. Return to the previous focus value')
                            
                # Exposure
                try:
                    result_exposure = action_exposure.run(frame_number = int(observation_status[filter_]['observed']),
                                                          exptime = float(exptime),
                                                          obsmode = obsmode,
                                                          filter_ = filter_,
                                                          specmode = specmode,
                                                          ntelescope = ntelescope,
                                                          gain = int(gain),
                                                          binning = int(binning),
                                                          imgtype = imgtype,
                                                        
                                                          ra = ra,
                                                          dec = dec,
                                                          alt = alt,
                                                          az = az,
                                                          name = name,
                                                          objtype = objtype,
                                                          id_ = id_,
                                                          note = note)
                    self._log.info(f'Debugging point 9')

                    # Update self.observation_status
                    observation_status[filter_]['observed'] += 1
                    self.shared_memory['status'] = observation_status
                    result_all_exposure.append(result_exposure)
                except ConnectionException:
                    self.is_running = False
                    self._log.critical(f'==========LV2[{type(self).__name__}] is failed: camera is disconnected.')
                    raise ConnectionException(f'[{type(self).__name__}] is failed: camera is disconnected.')
                except AbortionException:
                    self.abort()
                except ActionFailedException:
                    self.is_running = False
                    self._log.critical(f'==========LV2[{type(self).__name__}] is failed: exposure failure.')
                    raise ActionFailedException(f'[{type(self).__name__}] is failed: exposure failure.')
        self.shared_memory['succeeded'] = all(result_all_exposure)
        self.is_running = False
        
        self._log.info(f'==========LV2[{type(self).__name__}] is finished')
        return all(result_all_exposure)

    def abort(self):
        self.abort_action.set()
        self.is_running = False
        self._log.warning(f'==========LV2[{type(self).__name__}] is aborted.')
        raise AbortionException(f'[{type(self).__name__}] is aborted.')
        
    def _exposureinfo_to_list(self,
                              filter_ : str,
                              exptime : str,
                              count : str,
                              binning : str):
        filter_list = filter_.split(',')
        exptime_list = exptime.split(',')
        count_list = count.split(',')
        binning_list = binning.split(',')
        exposure_info = dict()
        exposure_info['filter_'] = filter_list
        exposure_info['exptime'] = exptime_list
        exposure_info['count'] = count_list
        exposure_info['binning'] = binning_list
        len_filt = len(filter_list)        
        for name, value in exposure_info.items():
            len_value = len(value)
            if len_filt != len_value:
                exposure_info[name] = [value[0]] * len_filt
        return exposure_info
    
    def _set_observation_status(self,
                                filter_ : str,
                                exptime : str,
                                count : str,
                                binning : str):
        exposureinfo = self._exposureinfo_to_list(filter_ = filter_, exptime= exptime, count = count, binning = binning)
        observation_status = dict()
        for filt, count in zip(exposureinfo['filter_'], exposureinfo['count']):
            observation_status[filt] = dict()
            observation_status[filt]['triggered'] = int(count)
            observation_status[filt]['observed'] = 0 
        return observation_status


# %%
if __name__ == '__main__':
    from tcspy.action.level1 import Connect
    telescope = SingleTelescope(21)
    abort_action = Event()
    C = Connect(telescope, abort_action)
    C.run()
    S = SingleObservation(telescope, abort_action)

#%%    
if __name__ == '__main__':

    kwargs = dict(
    exptime= '5,5',
    count= '1,1',
    filter_ = 'g,r',
    binning= '2,2',
    imgtype = 'Light',
    ra= None,
    dec= None,
    alt = 40,
    az = 300,
    name = "COSMOS",
    objtype = 'Commissioning',
    autofocus_before_start= True,
    autofocus_when_filterchange= True)              
    from multiprocessing import Process
    abort_action = Event()
    s = SingleObservation(SingleTelescope(21),abort_action)
    p = Process(target = s.run, kwargs = kwargs)
    p.start()
# %%
if __name__ == '__main__':
    s.abort()
# %%
if __name__ == '__main__':
    kwargs = dict(exptime = '5,5', 
                count = '2,2', 
                filter_ = 'g,r', 
                binning = '1', 
                imgtype = 'Light',
                ra = 200.5, 
                dec = -58.0666 , 
                obsmode = 'Single',
                autofocus_before_start = False, 
                autofocus_when_filterchange= False,
                observation_status = None)
    from multiprocessing import Process
    s = SingleObservation(SingleTelescope(7),Event())
    p = Process(target = s.run, kwargs = kwargs)
    p.start()
#%%