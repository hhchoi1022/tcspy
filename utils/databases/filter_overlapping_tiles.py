
#%%

from astropy.coordinates import SkyCoord
import astropy.units as u
import shapely.geometry as geom
from astropy.io import ascii
from astropy.table import Table
import matplotlib.pyplot as plt
from descartes import PolygonPatch
import numpy as np

#%%
def find_overlapping_tiles(tbl1, tbl2, 
                            FOV_RA_tbl1=None, 
                            FOV_Dec_tbl1=None, 
                            FOV_RA_tbl2=None, 
                            FOV_Dec_tbl2=None, 
                            overlap_threshold=0.5,
                            find_non_overlap : bool = True,
                            plot_tile_id : bool = False,
                            tile_id_key: str = 'id',
                            tile_id_fontsize: int = 10):
    """
    Filters tiles from the second table that overlap more than a threshold percentage 
    with any tiles from the first table, using spherical geometry for accurate corner calculation.
    
    Parameters:
    - tbl1: astropy.Table containing ra1, ra2, ra3, ra4, dec1, dec2, dec3, dec4 or central ra, dec for telescope 1
    - tbl2: astropy.Table containing ra1, ra2, ra3, ra4, dec1, dec2, dec3, dec4 or central ra, dec for telescope 2
    - FOV_RA_tbl1, FOV_Dec_tbl1: Field of View (RA, Dec) for telescope 1 if corners are not present
    - FOV_RA_tbl2, FOV_Dec_tbl2: Field of View (RA, Dec) for telescope 2 if corners are not present
    - overlap_threshold: float, overlap percentage threshold (default is 0.5 for 50%)
    
    Returns:
    - filtered_tbl2: astropy.Table containing the filtered tiles from tbl2
    """
    
    # Helper function to create corners using spherical geometry
    def create_corners_from_center(ra, dec, FOV_RA, FOV_Dec):
        # Create SkyCoord for the center of the tile
        center = SkyCoord(ra=ra*u.deg, dec=dec*u.deg, frame='icrs')
        
        # Calculate the four corners of the field of view using offsets
        corners = []
        offsets = [(-FOV_RA/2, FOV_Dec/2),  # Top-left
                   (FOV_RA/2, FOV_Dec/2),   # Top-right
                   (FOV_RA/2, -FOV_Dec/2),  # Bottom-right
                   (-FOV_RA/2, -FOV_Dec/2)] # Bottom-left
        
        for offset in offsets:
            corner = center.spherical_offsets_by(offset[0]*u.deg, offset[1]*u.deg)
            corners.append((corner.ra.deg, corner.dec.deg))
        
        return corners
    
    # Process tbl1, check if it contains corner coordinates or needs to generate from center
    def create_polygons(table, FOV_RA=None, FOV_Dec=None):
        tiles = []
        if 'ra1' in table.colnames and 'dec1' in table.colnames:  # Check if corners are present
            tiles = [
                [(table['ra1'][i], table['dec1'][i]), 
                 (table['ra2'][i], table['dec2'][i]), 
                 (table['ra3'][i], table['dec3'][i]), 
                 (table['ra4'][i], table['dec4'][i])]
                for i in range(len(table))
            ]
        elif 'ra' in table.colnames and 'dec' in table.colnames and FOV_RA is not None and FOV_Dec is not None:
            # If no corner data, generate corners from center ra/dec using FOV_RA and FOV_Dec
            tiles = [
                create_corners_from_center(table['ra'][i], table['dec'][i], FOV_RA, FOV_Dec)
                for i in range(len(table))
            ]
        else:
            raise ValueError("Table must contain either corner coordinates or central (ra, dec) with FOV info.")
        
        return [geom.Polygon(corners) for corners in tiles]

    # Create polygons for each tile in tbl1 and tbl2
    telescope1_polygons = create_polygons(tbl1, FOV_RA_tbl1, FOV_Dec_tbl1)
    telescope2_polygons = create_polygons(tbl2, FOV_RA_tbl2, FOV_Dec_tbl2)

    # List to store indices of tiles from tbl2 that are not overlapping more than the threshold
    non_overlap_indices = []
    overlap_indices = []

    #overlap_polygons = []

    for i, tile2_poly in enumerate(telescope2_polygons):
        overlap = False
        for tile1_poly in telescope1_polygons:
            # Check if polygons intersect
            if tile1_poly.intersects(tile2_poly):
                intersection_area = tile1_poly.intersection(tile2_poly).area
                tile2_area = tile2_poly.area
                # Calculate overlap percentage
                overlap_percentage = intersection_area / tile2_area
                if overlap_percentage > overlap_threshold:
                    overlap = True
                    #overlap_polygons.append(tile2_poly)
                    break
        if not overlap:
            non_overlap_indices.append(i)
        else:
            overlap_indices.append(i)

    # Create filtered table by selecting only valid indices
    overlap_tbl = tbl2[overlap_indices]
    non_overlap_tbl = tbl2[non_overlap_indices]
    overlap_polygons = [telescope2_polygons[i] for i in overlap_indices]
    non_overlap_polygons = [telescope2_polygons[i] for i in non_overlap_indices]

        # Plot the tiles using matplotlib polygons
    fig, ax = plt.subplots(figsize=(10, 8))

    # Helper function to plot polygons using matplotlib
    def plot_polygon(ax, polygon, edgecolor='black', facecolor='none', lw=1, linestyle='-', tile_id = None):
        x, y = polygon.exterior.xy
        ax.plot(x, y, color=edgecolor, lw=lw, linestyle=linestyle)
        ax.fill(x, y, color=facecolor, alpha=0.5 if facecolor != 'none' else 0)
        if plot_tile_id:
            position = (1.35*np.min(x) + 0.65*np.max(x))/2, (np.min(y) + np.max(y))/2
            ax.text(position[0], position[1], tile_id, fontsize=tile_id_fontsize, color='black')

    # Plot tbl1 tiles (black)
    for poly, tile_id in zip(telescope1_polygons, tbl1[tile_id_key]):
        plot_polygon(ax, poly, edgecolor='blue', lw =3, tile_id = tile_id)

    # Plot tbl2 tiles (black dashed)
    for poly, tile_id in zip(telescope2_polygons, tbl2[tile_id_key]):
        plot_polygon(ax, poly, edgecolor='black', tile_id = tile_id)

    # Plot overlapping tiles (red)
    for poly, tile_id in zip(overlap_polygons, overlap_tbl[tile_id_key]):
        plot_polygon(ax, poly, edgecolor='red', facecolor='red', tile_id = tile_id)

    #ax.set_xlim(0, 360)
    #ax.set_ylim(-90, 90)
    ax.set_xlabel('Right Ascension (RA)')
    ax.set_ylabel('Declination (Dec)')
    ax.set_title('Sky Tiles: Black = All tiles, Red = Overlapping tiles')

    plt.grid(True)
    plt.show() 
    if find_non_overlap:
        return non_overlap_tbl
    else:
        return overlap_tbl
#%%
# Example usage
if __name__ == "__main__":
    # Read the astropy tables
    from astropy.io import ascii
    from astropy.table import Table
    tbl1 = Table()
    tbl1['id'] = ['WDFS0122-30']
    target_ra = 327.88467
    target_dec = -56.66531
    tbl1['ra'] = [target_ra]
    tbl1['dec']  = [target_dec]
    #tbl1 = ascii.read('~/Downloads/Subset_White_Dwarfs_with_Matched_Tiles.csv')
    #tbl1.rename_column('name', 'id')


    tbl2_original = ascii.read('./databases/sky-grid and tiling/7-DT/final_tiles.txt')
    ra_cut = 2
    dec_cut = 2
    tbl2_idx = (tbl2_original['ra'] > target_ra-ra_cut) & (tbl2_original['ra'] < target_ra+ra_cut) & (tbl2_original['dec'] > target_dec-dec_cut) & (tbl2_original['dec'] < target_dec+dec_cut)
    tbl2 = tbl2_original[tbl2_idx]
    #tbl2.remove_columns(['ra1', 'dec1', 'ra2', 'dec2', 'ra3', 'dec3', 'ra4', 'dec4'])

    # Specify FOV values for the two telescopes (in degrees)
    FOV_RA_tbl1 = 0.01  # Example FOV_RA for tbl1
    FOV_Dec_tbl1 = 0.01  # Example FOV_Dec for

    tilelist = []
    for tbl_1 in tbl1:
        target_ra = tbl_1['ra']
        target_dec = tbl_1['dec']
        tbl2_idx = (tbl2_original['ra'] > target_ra-ra_cut) & (tbl2_original['ra'] < target_ra+ra_cut) & (tbl2_original['dec'] > target_dec-dec_cut) & (tbl2_original['dec'] < target_dec+dec_cut)
        tbl2 = tbl2_original[tbl2_idx]
        # Filter tiles from tbl2 based on overlap with tbl1
        filtered_tbl2 = find_overlapping_tiles(tbl1 = Table(tbl_1), tbl2 = tbl2,
                                                FOV_RA_tbl1 = FOV_RA_tbl1,
                                                FOV_Dec_tbl1 = FOV_Dec_tbl1,
                                                    
                                            overlap_threshold = 0,
                                            find_non_overlap=False,
                                            plot_tile_id=True,
                                            tile_id_fontsize= 10)
        tilelist.append(filtered_tbl2[0]['id'])



# %%
