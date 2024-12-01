

#%%
from astropy.io import ascii
from astropy.coordinates import SkyCoord
import astropy.units as u
import shapely.geometry as geom
from astropy.io import ascii
import matplotlib.pyplot as plt
from shapely.geometry import Point
import shapely
import numpy as np
import os
#%%
import os
import matplotlib.pyplot as plt
from shapely.geometry import Point, Polygon
from astropy.io import ascii
import numpy as np

class Tiles:
    def __init__(self, tile_path: str = None):
        if tile_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.tile_path = os.path.join(current_dir, './sky-grid and tiling/7-DT/final_tiles.txt')
        else:
            self.tile_path = tile_path
        self.tbl_RIS = None

    def find_overlapping_tiles(self, list_ra, list_dec, visualize: bool = True, visualize_ncols: int = 5):
        """
        Find the tiles that overlap with the given coordinates.

        Parameters:
        - list_ra: list of RA coordinates
        - list_dec: list of Dec coordinates
        - visualize (bool): Whether to visualize the overlapping tiles
        - visualize_ncols (int): Number of columns in the visualization grid

        Returns:
        - A table containing the innermost tiles for each coordinate.
        """
        
        

        def split_wrapping_polygon(polygon):
            """
            Splits a polygon into two parts if it crosses the RA = 0 (360) boundary.
            Ensures correct wrapping at the boundary and forms two valid polygons.

            Parameters:
            - polygon: Shapely Polygon object.

            Returns:
            - A list of Shapely Polygons split at the RA = 0 (360) boundary.
            """
            exterior_coords = list(polygon.exterior.coords)[:4]
            list_ra = [coord[0] for coord in exterior_coords]
            list_dec = [coord[1] for coord in exterior_coords]
            is_crossing = (np.max(list_ra) - np.min(list_ra)) > 180
            if not is_crossing:
                return [polygon]
            else:
                # Contruct polygons for the two parts
                left_part = []  # Coordinates for the part near RA = 0
                right_part = []  # Coordinates for the part near RA = 360
                left_part_idx = [0,1]
                right_part_idx = [2,3]
                for idx_left in left_part_idx:
                    left_part.append(exterior_coords[idx_left])
                left_part.append([0, left_part[1][1]])
                left_part.append([0, left_part[0][1]])
                left_part.append(left_part[0])
                for idx_right in right_part_idx:
                    right_part.append(exterior_coords[idx_right])
                right_part.append([360, right_part[1][1]])
                right_part.append([360, right_part[0][1]])
                right_part.append(right_part[0])
                # Create polygons
                polygons = []
                if len(left_part) > 2:
                    polygons.append(Polygon(left_part))
                if len(right_part) > 2:
                    polygons.append(Polygon(right_part))

                return polygons


        def create_polygons(table):
            """
            Create polygons for the tiles, splitting them if necessary.
            """
            polygons_by_id = {}
            for i, row in enumerate(table):
                corners = [
                    (row['ra1'], row['dec1']),
                    (row['ra2'], row['dec2']),
                    (row['ra3'], row['dec3']),
                    (row['ra4'], row['dec4']),
                ]
                split_polygons = split_wrapping_polygon(Polygon(corners))
                polygons_by_id[i] = split_polygons

            return polygons_by_id

        def calculate_innermost_tile(polygons_by_id, target_point):
            """
            Determine the innermost tile for a given target point.
            """
            max_distance = -float('inf')
            innermost_tile_id = None

            for tile_id, polygons in polygons_by_id.items():
                for poly in polygons:
                    if poly.contains(target_point) or poly.boundary.contains(target_point):
                        distance_to_boundary = target_point.distance(poly.boundary)
                        if distance_to_boundary > max_distance:
                            max_distance = distance_to_boundary
                            innermost_tile_id = tile_id
            return innermost_tile_id


        # Load the tile data
        self.tbl_RIS = ascii.read(self.tile_path)
        RIS_polygons_by_id = create_polygons(self.tbl_RIS)

        # Find innermost tiles
        innermost_indices = []
        matched_coord_indices = []
        for i, (ra, dec) in enumerate(zip(list_ra, list_dec)):
            target_point = Point(ra, dec)
            innermost_tile_id = calculate_innermost_tile(RIS_polygons_by_id, target_point)
            if innermost_tile_id is not None:
                innermost_indices.append(innermost_tile_id)
                matched_coord_indices.append(i)

        if visualize:
            self.visualize_tiles(
                list_ra, list_dec, RIS_polygons_by_id, matched_coord_indices, innermost_indices, visualize_ncols)

        return self.tbl_RIS[innermost_indices]
    
    def visualize_tiles(self, list_ra, list_dec, polygons_by_id, matched_coord_indices, innermost_indices, visualize_ncols):
        """
        Visualize the tiles and matched coordinates with tile names and a legend.
        """
        list_ra = [list_ra[i] for i in matched_coord_indices]
        list_dec = [list_dec[i] for i in matched_coord_indices]

        def select_polygons_within_bbox(polygons_by_id, center, radius=4):
            """
            Select polygons that are within a specified radius from the center point.
            """
            minx, miny = (center.x - radius + 360) % 360, center.y - radius
            maxx, maxy = (center.x + radius + 360) % 360, center.y + radius
                
            bbox = Polygon([(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy)])

            selected_polygons = []
            selected_ids = []

            for tile_id, polygons in polygons_by_id.items():
                for poly in polygons:
                    if poly.intersects(bbox):
                        selected_polygons.append(poly)
                        selected_ids.append(tile_id)
                        break

            return selected_polygons, selected_ids

        RIS_tilenames = self.tbl_RIS['id']

        n_coords = len(list_ra)
        cols = visualize_ncols
        rows = (n_coords + cols - 1) // cols

        fig, axes = plt.subplots(rows, cols, figsize=(15, rows * 3), subplot_kw={'aspect': 'equal'})
        if rows == 1 and cols == 1:
            axes = [axes]
        elif isinstance(axes, np.ndarray):
            axes = axes.flatten()

        for i, (ra, dec) in enumerate(zip(list_ra, list_dec)):
            ax = axes[i]
            center_point = Point(ra, dec)
            selected_polygons, selected_ids = select_polygons_within_bbox(polygons_by_id, center_point, radius=2)

            # Plot surrounding polygons in blue
            for poly, tile_id in zip(selected_polygons, selected_ids):
                x, y = poly.exterior.xy
                ax.plot(x, y, color='blue', lw=1)  # Add label only once
                ax.fill(x, y, color='blue', alpha=0.3)
                
                # Annotate tile name near the centroid
                centroid = poly.centroid
                tile_name = RIS_tilenames[tile_id]
                #ax.text(centroid.x, centroid.y, tile_name, fontsize=8, ha='center', va='center', color='black', bbox=dict(facecolor='white', alpha=0.6, edgecolor='none'))

            # Highlight the innermost polygon in red
            if i < len(innermost_indices):
                innermost_tile_id = innermost_indices[i]
                innermost_poly = polygons_by_id[innermost_tile_id][0]
                x, y = innermost_poly.exterior.xy
                ax.plot(x, y, color='red', lw=2)
                centroid = innermost_poly.centroid
                tile_name = RIS_tilenames[innermost_tile_id]
                ax.text(centroid.x, centroid.y, tile_name, fontsize=8, ha='center', va='center', color='black',
                        bbox=dict(facecolor='white', alpha=0.6, edgecolor='none'))

            # Plot the target point
            ax.scatter(ra, dec, color='green', marker='o', s=50, label='Target Point' if i == 0 else None)

            ax.set_xlim(ra - 2, ra + 2)
            ax.set_ylim(dec - 2, dec + 2)
            ax.set_title(f'Target {i+1}: ({ra:.2f}, {dec:.2f})')

        # Add a legend to the first subplot
        axes[0].legend(loc='upper left', fontsize=8)

        # Remove unused subplots
        for j in range(len(list_ra), len(axes)):
            fig.delaxes(axes[j])

        plt.tight_layout()
        plt.show()



# %%
# Example usage
if __name__ == "__main__":
    T = Tiles()
    #tbl_filter = T.find_overlapping_tiles([40, 20, 30], [-85.15, -40, -50], visualize=True, visualize_ncols=5)
    tbl1 = ascii.read('~/Downloads/Subset_White_Dwarfs_with_Matched_Tiles.csv')

    list_ra = tbl1['ra']
    list_dec = tbl1['dec']
    tbl_filter =T.find_overlapping_tiles(list_ra, list_dec, visualize=True, visualize_ncols=5)
    # Read the astropy tables
    from astropy.io import ascii
    from astropy.table import Table
    tbl1 = Table()
    tbl1['id'] = ['WDFS0122-30']
    target_ra = 327.88467
    target_dec = -56.66531
    tbl1['ra'] = [target_ra]
    tbl1['dec']  = [target_dec]
    tbl1 = ascii.read('~/Downloads/Subset_White_Dwarfs_with_Matched_Tiles.csv')
    tbl1.rename_column('name', 'id')


    tbl2_original = ascii.read('./sky-grid and tiling/7-DT/final_tiles.txt')
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
