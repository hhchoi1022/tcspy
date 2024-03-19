#%%
from astropy.io import ascii
from astropy.coordinates import SkyCoord
import astropy.units as u
#%%
def Load_IMSNG(filename : str,
               format_ : str = 'fixed_width'):
    all_targets = ascii.read(filename, format = format_)
    name = all_targets['obj']
    ra_hms = all_targets['ra']
    dec_dms = all_targets['dec']
    coord = SkyCoord(ra_hms, dec_dms, unit = (u.hourangle, u.degree), frame ='icrs')
    ra_hour = coord.ra.hour.round(5)
    dec_deg = coord.dec.deg.round(5)
    all_targets['project'] = 'IMSNG'
    project = all_targets['project']
    note = all_targets['note']
    data = dict(name = name,
                ra_hms = ra_hms,
                dec_dms = dec_dms,
                ra_hour = ra_hour,
                dec_deg = dec_deg,
                project = project,
                note = note
                )
    return data

# %%
