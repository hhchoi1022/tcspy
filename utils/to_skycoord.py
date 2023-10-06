import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as u
def to_SkyCoord(ra, dec,
                frame = 'icrs'):
    '''
    parameters
    ----------
    1. ra : str or float
            Right ascension in diverse format(see notes)
    2. dec : str or float
            Declination in diverse format(see notes)
    
    returns 
    -------
    1. skycoord : SkyCoord
    
    notes 
    -----
    Current supported formats
        1. 15h32m10s, 50d15m01s
        2. 15 32 10, 50 15 01
        3. 15:32:10, 50:15:01
        4. 230.8875, 50.5369
    -----
    '''
    if isinstance(ra, float) | isinstance(ra, int) | isinstance(ra, str) | isinstance(ra, np.str_):
        ra = str(ra) ; dec = str(dec)
        if (':' in ra) & (':' in dec):
            skycoord = SkyCoord(ra = ra, dec = dec, unit = (u.hourangle, u.deg), frame = frame)
        elif ('h' in ra) & ('d' in dec):
            skycoord = SkyCoord(ra = ra, dec = dec, unit = (u.hourangle, u.deg), frame = frame)
        elif (' ' in ra) & (' ' in dec):
            skycoord = SkyCoord(ra = ra, dec = dec, unit = (u.hourangle, u.deg), frame = frame)
        else:
            skycoord = SkyCoord(ra = ra, dec = dec, unit = (u.deg, u.deg), frame = frame)
    else:
        if isinstance(type(ra[0]), str) | isinstance(type(ra[0]), np.str_):
            if (':' in ra[0]) & (':' in dec[0]):
                skycoord = SkyCoord(ra = ra, dec = dec, unit = (u.hourangle, u.deg), frame = frame)
            elif ('h' in ra[0]) & ('d' in dec[0]):
                skycoord = SkyCoord(ra = ra, dec = dec, unit = (u.hourangle, u.deg), frame = frame)
            elif (' ' in ra[0]) & (' ' in dec[0]):
                skycoord = SkyCoord(ra = ra, dec = dec, unit = (u.hourangle, u.deg), frame = frame)
        else:
            skycoord = SkyCoord(ra = ra, dec = dec, unit = (u.deg, u.deg), frame = frame)
    return skycoord