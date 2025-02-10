#%%
import glob
import astropy.io.fits as fits
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from ccdproc import ImageFileCollection
import os
#%%
# Define file search pattern
file_pattern = '/lyman/data1/obsdata/7DT??/2025-02-06*/*_T?????_*.fits'

file_pattern = '/data2/obsdata/7DT??/image/2025-02-07*/*_T?????_*.fits'
all_files = glob.glob(file_pattern)

# Get the parent directories
directories = list(set(os.path.dirname(file) for file in all_files))
#%%

def load_collection(file_pattern, return_only_light = True):
    from astropy.table import Table, vstack
    
    # Define file search pattern
    all_files = glob.glob(file_pattern)

    # Get unique parent directories
    directories = list(set(os.path.dirname(file) for file in all_files))
    
    # Initialize an empty list to store all file paths
    all_coll = Table()

    # Iterate through directories and collect FITS file paths
    for directory in directories:
        coll = ImageFileCollection(location=directory, glob_include='*.fits')
        if len(coll.files) > 0:
            print(f"Loaded {len(coll.files)} FITS files from {directory}")

            # Convert summary table to a uniform format
            summary = coll.summary.copy()

            # Ensure all string columns are explicitly converted to `str`
            for colname in summary.colnames:
                col_dtype = summary[colname].dtype
                if col_dtype.kind in ('O', 'U', 'S'):  # Object, Unicode, or String types
                    summary[colname] = summary[colname].astype(str)
                elif col_dtype.kind in ('i', 'f'):  # Integer or Float types
                    summary[colname] = summary[colname].astype(str)  # Convert to string for consistency
                    summary[colname].fill_value = ''  # Ensure NaN values are handled
            # Stack tables
            if all_coll is None:
                all_coll = summary
            else:
                all_coll = vstack([all_coll, summary], metadata_conflicts='silent')

        else:
            print(f"Warning: No FITS files found in {directory}")

    # Check final count of combined FITS files
    print(f"Total FITS files combined: {len(all_coll)}")
    if return_only_light:
        all_coll = all_coll[all_coll['imagetyp'] == 'LIGHT']
    return all_coll
#%%
all_coll = load_collection(file_pattern)
all_coll = all_coll[all_coll['objtype'] == 'GECKO']
# %%
all_coll.write('250207.ascii', format='ascii', overwrite=True)
# %%
