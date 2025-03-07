

#%%
import json
import os
import glob

from astropy.io import fits
from astropy.table import Table
from astropy.table import vstack
from astropy.time import Time
from astropy.stats import sigma_clip

import matplotlib.pyplot as plt
import numpy as np
import datetime
from tqdm import tqdm

#%%

class FocusModel:
    
    def __init__(self, 
                 unitnum : int,
                 configpath : str = '/home/kds/tcspy/configuration/',
                 filtinfo_file : str = './filtinfo.data',
                 offset_file : str = 'filter.offset'):
        self.unitnum = unitnum
        self.name_telescope = '7DT%.2d' % self.unitnum
        self._filterinfo = self._read_json(filtinfo_file)
        self.filters = self._filterinfo[self.name_telescope]
        self._offset_file = os.path.join(configpath,self.name_telescope,offset_file)
        self.is_exist_offset = os.path.isfile(self._offset_file)
        self.offsets = None
        self.errors = None
        if self.is_exist_offset:
            data = self._read_json(self._offset_file)
            data.pop('updated_date')
            keys = list(data.keys())
            self.offsets = [data[key]['offset'] for key in keys]
            self.errors = [data[key]['error'] for key in keys]
        
    def _read_json(self, file):
        with open(file, 'r') as f:
            filtinfo_dict = json.load(f)
        return filtinfo_dict

    def _write_json(self, dict, file):
        with open(file, 'w') as f:
           json.dump(dict, f, indent = 4)
    
    def _format_offset(self,
                       list_filters : list,
                       list_offsets : list = None,
                       list_errors : list = None):
        if list_offsets == None:
            list_offsets = [999] * len(list_filters)
        if list_errors == None:
            list_errors = [999] * len(list_filters)
        elif len(list_filters) != len(list_offsets):
            raise AttributeError(f'len(list_offsets)[{len(list_filters)}] is not identical to len(list_filters)[{len(list_offsets)}]')
        format_ = dict()
        format_['updated_date'] = Time.now().isot
        for filter_, offset, error in zip(list_filters, list_offsets, list_errors):
            data = dict()
            data['offset'] = offset
            data['error'] = error
            format_[filter_] = data
        return format_

    def calc_model_params(self,
                          folder : str,
                          file_key : str = '*.fits',
                          filter_offset_zero : str = 'r',
                          start_obsdate : Time = Time('2023-01-01'),
                          end_obsdate : Time = Time.now(),
                          focusval_key : str = 'FOCUSPOS',
                          obsdate_key : str = 'DATE-LOC',
                          filter_key : str = 'FILTER',
                          temperature_key : str = None,
                          visualize : bool = True):
        '''
        folder = '/large_data/obsdata/7DT09/'
        file_key = '*.fits'
        start_obsdate : Time = Time('2024-01-01')
        end_obsdate : Time = Time.now()
        focusval_key : str = 'FOCUSPOS'
        obsdate_key : str = 'DATE-LOC'
        filter_key : str = 'FILTER'
        temperature_key : str = None
        visualize : bool = True
        '''
        # submodule for matching two astropy tables based on specific key & tolerance
        def match_table(tbl1, tbl2, key, tolerance = 0.01):
            from astropy.table import hstack
            
            
            '''
            parameters
            ----------
            {two tables} to combine with the difference of the {key} smaller than the {tolerance}
            
            returns 
            -------
            1. combined table
            2. phase

            notes 
            -----
            Combined table have both columns of original tables. 
            They are horizontally combined in the order of tbl1, tbl2
            -----
            '''
             
            matched_tbl = Table()
            for obs in tbl1:
                ol_idx = (np.abs(obs[key] - tbl2[key]) < tolerance)
                if True in ol_idx:
                    closest_idx = np.argmin(np.abs(obs[key]-tbl2[key]))
                    compare_tbl = tbl2[closest_idx]
                    compare_tbl = hstack([obs, compare_tbl])#join(obs, compare_tbl, keys = 'observatory', join_type = 'outer')
                    matched_tbl = vstack([matched_tbl, compare_tbl])

            return matched_tbl
        
        def get_filelist_in_duration(folder : str,
                                     start_obsdate : Time,
                                     end_obsdate : Time,
                                     file_key : str, 
                                     format_dt = ['%Y-%m-%d', '%Y%m%d', '%y-%m-%d', '%y%m%d']):
            dirlist = os.listdir(folder)
            dirlist_in_duration = []
            dt_list = []
            for format_component in format_dt:
                for dirname in dirlist:
                    try:
                        dt = datetime.datetime.strptime(dirname, format_component)
                        dt_list.append(dt)
                        dirlist_in_duration.append(dirname)
                    except:
                        pass
            dir_index = (start_obsdate < Time(dt_list)) & (Time(dt_list) < end_obsdate)
            dirlist_in_duration = np.array(dirlist_in_duration)[dir_index]
            filekeylist_in_duration = [os.path.join(folder, dirname, file_key) for dirname in dirlist_in_duration]
            files_in_duration = []
            for filekey in filekeylist_in_duration:
                filelist = glob.glob(filekey)
                files_in_duration.extend(filelist)
            return files_in_duration
            
        # Collect data for the calculation
        print(f"Counting images... \n Duration = {start_obsdate.isot} - {end_obsdate.isot}")
        imagelist = get_filelist_in_duration(folder, start_obsdate = start_obsdate, end_obsdate = end_obsdate, file_key = file_key)
        print(f"{len(imagelist)} images are found")
        all_obsdate = []
        all_focusval = []
        all_filter = []
        all_obsdatetime = []
        all_temp = []
        imlist = []
        pbar = tqdm(imagelist)
        for image in pbar:
            pbar.set_description("Collecting header information...")
            image_hdr = fits.getheader(image)
            obsdate = Time(image_hdr[obsdate_key])
            try:
                focusval = image_hdr[focusval_key]
                filter_ = image_hdr[filter_key]
                imlist.append(image)
                all_obsdate.append(obsdate)
                all_obsdatetime.append(obsdate)
                all_focusval.append(focusval)
                all_filter.append(filter_)                
                if temperature_key:
                    temperature = image_hdr[temperature_key]
                else:
                    temperature = None
                all_temp.append(temperature)
            except:
                pass
        tbl = Table()
        tbl['image'] = imlist
        tbl['obsdate'] = all_obsdatetime
        tbl['focus'] = all_focusval
        tbl['filter_'] = all_filter
        tbl['temperature'] = all_temp
        tbl.sort('obsdate')
        # cut sample with the obstime > start_obsdate & obstime < end_obsdate
        tbl = tbl[(tbl['obsdate'] > start_obsdate) & (tbl['obsdate'] < end_obsdate)]
        first_obsdate = tbl['obsdate'][0]
        tbl['obsdate_relative'] = (tbl['obsdate'] - first_obsdate).value
        duration_obs = tbl['obsdate_relative'][-1]
        
        # Binning
        tbl_binning = Table()
        previous_focus = None
        for row in tbl:
            current_focus = row['focus']
            if current_focus != previous_focus:
                tbl_binning = vstack([tbl_binning, row], join_type = 'outer')
            previous_focus = current_focus
        
        # Groupping by filters
        tbl_filter_dict = dict()
        for filter_ in self.filters:
            tbl_filter_dict[filter_] = tbl_binning[tbl_binning['filter_'] == filter_]
        
        # Setting color for each filter
        colorset = ['red','peru','darkorange','green','deeppink','teal','navy','blueviolet','dodgerblue', 'blue', 'black']
        filter_color = dict()
        for i, filter_ in enumerate(self.filters):
            filter_color[filter_] = colorset[i]

        # Calculate focus offsets based on first filters
        print('Calculating filter offset...')
        focusdiffmean_all = []
        focusdiffstd_all = []
        if visualize:
            plt.figure(dpi = 300, figsize = (6,4))
        for filter_ in self.filters:
            tbls_matched = match_table(tbl_filter_dict[filter_], tbl_filter_dict[filter_offset_zero], key = 'obsdate', tolerance = 0.3)
            if len(tbls_matched)>0:
                tbls_matched['focusdiff'] = tbls_matched['focus_1']-tbls_matched['focus_2']
                sigma_clip_mask = sigma_clip(tbls_matched['focusdiff'], sigma_lower =2, sigma_upper=2, masked = True).mask
                tbl_clipped = tbls_matched[~sigma_clip_mask]
                focusdiff_mean = int(np.mean(tbl_clipped['focusdiff']))
                focusdiff_std = int(np.std(tbl_clipped['focusdiff']))
                focusdiffmean_all.append(focusdiff_mean)
                focusdiffstd_all.append(focusdiff_std)
                ####################### update params not offset
                ####################### TODO #######################
                if visualize:
                    plt.scatter(tbl_clipped['obsdate_relative_1'],tbl_clipped["focusdiff"], c = filter_color[filter_])
                    plt.axhline(focusdiff_mean, c = filter_color[filter_], linestyle = '--')
                    plt.fill_between((-3, duration_obs+3), focusdiff_mean-focusdiff_std , focusdiff_mean+focusdiff_std, color = filter_color[filter_], alpha = 0.3)
                    plt.text(duration_obs+2.2, focusdiff_mean -0.2*focusdiff_std, s = rf'{filter_} : {focusdiff_mean}$\pm${focusdiff_std}', color = filter_color[filter_])
            else:
                focusdiffmean_all.append(999)
                focusdiffstd_all.append(999)
        if visualize:
            plt.title(f'Focus offset of {self.name_telescope}')
            plt.xticks(rotation = 45)
            plt.xlim(-2, duration_obs +2)
            plt.xlabel(f'Days since {first_obsdate}')
            plt.ylabel(f'Offset to {self.filters[0]} filter')
            plt.savefig(f'OFFSET_{self.name_telescope}.png')
        return focusdiffmean_all, focusdiffstd_all
    
    def update_params(self,
                      list_offsets : list = None,
                      list_errors : list = None):
        filter_info = self._filterinfo[self.name_telescope]
        format_offset_dict = self._format_offset(list_filters = filter_info, list_offsets = list_offsets, list_errors = list_errors)
        self._write_json(dict = format_offset_dict, file = self._offset_file)
        print(f'{self._offset_file} is updated')
# %%
if __name__ == '__main__':
    unitnum = 3
    FModel = FocusModel(unitnum)
    #folder = '/large_data/obsdata/7DT%.2d' %unitnum
    #offset_vallist, offset_stdlist = FModel.calc_model_params(folder, start_obsdate = Time('2024-02-20'))
    #FModel.update_params(None, None)
    #FModel.update_params(offset_vallist, offset_stdlist)
#%%