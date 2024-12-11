

#%%
from astropy.coordinates import SkyCoord
import astropy.units as u
import shapely.geometry as geom
import shapely
import os
import matplotlib.pyplot as plt
from shapely.geometry import Point, Polygon
from astropy.io import ascii
from astropy.table import Table

import numpy as np
import datetime

class Tiles:
    def __init__(self, tile_path: str = None):
        if tile_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.tile_path = os.path.join(current_dir, './sky-grid and tiling/7-DT/final_tiles.txt')
        else:
            self.tile_path = tile_path
        self.tbl_RIS = None
        self.coords_RIS = None

    def find_overlapping_tiles(self, list_ra, list_dec, visualize: bool = True, visualize_ncols: int = 5, visualize_savepath: str = './tiles'):
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
        if not self.tbl_RIS:
            self.tbl_RIS = ascii.read(self.tile_path)
        if not self.coords_RIS:
            self.coords_RIS = SkyCoord(ra=self.tbl_RIS['ra'], dec=self.tbl_RIS['dec'], unit=(u.deg, u.deg))
            
        # Find innermost tiles
        innermost_indices = []
        matched_coord_indices = []
        
        for i, (ra, dec) in enumerate(zip(list_ra, list_dec)):
            target_point = Point(ra, dec)
            coord_targets = SkyCoord(ra=ra, dec=dec, unit=(u.deg, u.deg))
            nearby_tiles_idx = coord_targets.separation(self.coords_RIS) < 5*u.deg
            RIS_polygons_nearby = self._create_polygons(self.tbl_RIS[nearby_tiles_idx])
            innermost_tile_id = calculate_innermost_tile(RIS_polygons_nearby, target_point)
            if innermost_tile_id is not None:
                innermost_indices.append(innermost_tile_id)
                matched_coord_indices.append(i)

        fig_path = None
        if visualize:
            fig_path = self.visualize_tiles(list_ra, list_dec, matched_coord_indices, innermost_indices, visualize_ncols, visualize_savepath)
            
        if len(matched_coord_indices) == 0:
            return Table(), matched_coord_indices, fig_path
        
        # Reorder based on the order of 'innermost_indices'
        matched_tbl = self.tbl_RIS[np.isin(self.tbl_RIS['id'], innermost_indices)]
        order = {id_: i for i, id_ in enumerate(innermost_indices)}
        sorted_rows = sorted(matched_tbl, key=lambda row: order[row['id']])
        ordered_table = Table(rows=sorted_rows, names=matched_tbl.colnames)

        return ordered_table, matched_coord_indices, fig_path
    
    def visualize_tiles(self, list_ra, list_dec, matched_coord_indices, innermost_indices, visualize_ncols, visualize_savepath):
        """
        Visualize the tiles and matched coordinates with tile names and a legend.
        """
        list_ra = [list_ra[i] for i in matched_coord_indices]
        list_dec = [list_dec[i] for i in matched_coord_indices]


        n_coords = len(list_ra)
        cols = visualize_ncols
        rows = (n_coords + cols - 1) // cols

        fig, axes = plt.subplots(rows, cols, figsize=(15, rows * 3), subplot_kw={'aspect': 'equal'})
        if rows == 1 and cols == 1:
            axes = [axes]
        elif isinstance(axes, np.ndarray):
            axes = axes.flatten()

        for i, (ra, dec, innermost_tile_id) in enumerate(zip(list_ra, list_dec, innermost_indices)):
            ax = axes[i]
            center_point = Point(ra, dec)
            coord_targets = SkyCoord(ra=ra, dec=dec, unit=(u.deg, u.deg))
            nearby_tiles_idx = coord_targets.separation(self.coords_RIS) < 3*u.deg
            nearby_polygons_by_id = self._create_polygons(self.tbl_RIS[nearby_tiles_idx])
            nearby_polygons = list(nearby_polygons_by_id.values())
            nearby_ids = list(nearby_polygons_by_id.keys())
            
            # Plot surrounding polygons in blue
            for polygons, tile_id in zip(nearby_polygons, nearby_ids):
                for poly in polygons:
                    x, y = poly.exterior.xy
                    ax.plot(x, y, color='blue', lw=1)  # Add label only once
                    ax.fill(x, y, color='blue', alpha=0.3)
                    
                    # Annotate tile name near the centroid
                    centroid = poly.centroid
                    tile_name = tile_id
                    #ax.text(centroid.x, centroid.y, tile_name, fontsize=8, ha='center', va='center', color='black', bbox=dict(facecolor='white', alpha=0.6, edgecolor='none'))

            # Highlight the innermost polygon in red
            innermost_poly = nearby_polygons_by_id[innermost_tile_id][0]
            x, y = innermost_poly.exterior.xy
            ax.plot(x, y, color='red', lw=2)
            centroid = innermost_poly.centroid
            ax.text(centroid.x, centroid.y, innermost_tile_id, fontsize=8, ha='center', va='center', color='black',
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
        if visualize_savepath:
            os.makedirs(visualize_savepath, exist_ok=True)
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            fig_path = f"{os.path.join(visualize_savepath, f'matched_tiles_{timestamp}')}.png"
            plt.savefig(fig_path)
        plt.show() 
        
    def _split_wrapping_polygon(self, polygon):
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


    def _create_polygons(self, table):
        """
        Create polygons for the tiles, splitting them if necessary.
        """
        polygons_by_id = {}
        for row in table:
            corners = [
                (row['ra1'], row['dec1']),
                (row['ra2'], row['dec2']),
                (row['ra3'], row['dec3']),
                (row['ra4'], row['dec4']),
            ]
            split_polygons = self._split_wrapping_polygon(Polygon(corners))
            polygons_by_id[row['id']] = split_polygons

        return polygons_by_id



# %%
# Example usage
if __name__ == "__main__":
    T = Tiles()
    #tbl_filter = T.find_overlapping_tiles([40, 20, 30], [-85.15, -40, -50], visualize=True, visualize_ncols=5)
    tbl1 = ascii.read('~/Downloads/Subset_White_Dwarfs_with_Matched_Tiles.csv')
    tbl1 = ascii.read('/Users/hhchoi1022/code/GECKO/S240925n/SkyGridCatalog_7DT_90.csv')

    list_ra = [tbl1[0]['ra']]#tbl1['ra'][0]
    list_dec = [tbl1[0]['dec']]#tbl1['dec'][0]
    #list_ra = [30]
    #list_dec = [-40]
    tbl_filtered, tbl_idx, fig_path =T.find_overlapping_tiles(list_ra, list_dec, visualize=False, visualize_ncols=5)  
# %%
