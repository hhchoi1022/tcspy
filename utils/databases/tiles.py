

#%%
from astropy.io import ascii
from astropy.coordinates import SkyCoord
import astropy.units as u
import shapely.geometry as geom
from astropy.io import ascii
import matplotlib.pyplot as plt
from shapely.geometry import Point
import shapely
import os
#%%

class Tiles:
    def __init__(self, 
                 tile_path: str = None):
        # Use the current file's directory to construct the default path
        if tile_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.tile_path = os.path.join(current_dir, './sky-grid and tiling/7-DT/final_tiles.txt')
        else:
            self.tile_path = tile_path
        self.tbl_RIS = None
    
    def find_overlapping_tiles(self,
                               list_ra,
                               list_dec, 
                               visualize : bool = True,
                               visualize_ncols : int = 5,
                               ):
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

        def split_wrapping_polygon(polygon):
            """
            Splits a polygon into two parts if it crosses the 0/360 boundary.
            Returns a list of polygons, either one (if no wrapping) or two (if it wraps).
            """
            exterior_coords = list(polygon.exterior.coords)
            wrapped_coords = []
            current_part = []

            for coord in exterior_coords:
                lon, lat = coord
                normalized_lon = lon % 360  # Ensure longitudes are in the 0–360 range

                if len(current_part) > 0 and abs(current_part[-1][0] - normalized_lon) > 180:
                    # Detected a wrap-around (e.g., from 359 to 0 or vice versa)
                    wrapped_coords.append(current_part)
                    current_part = []

                current_part.append((normalized_lon, lat))

            if current_part:
                wrapped_coords.append(current_part)

            # Create polygons from each segment
            polygons = [geom.Polygon(coords) for coords in wrapped_coords if len(coords) > 2]
            return polygons

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
            
            all_polygons = []
            for tile in tiles:
                all_polygons += split_wrapping_polygon(geom.Polygon(tile))
            
            return all_polygons
        
        def select_polygons_within_bbox(polygons, ids, center, radius=4):
            """
            Select polygons that are within a specified radius from the center point,
            handling 0/360 wrapping.
            """
            # Create a bounding box around the center point
            minx, miny = (center.x - radius + 360) % 360, center.y - radius
            maxx, maxy = (center.x + radius + 360) % 360, center.y + radius
            bbox = shapely.geometry.box(minx, miny, maxx, maxy)

            selected_polygons = []
            selected_ids = []

            for poly, id_ in zip(polygons, ids):
                # Handle wrapping by splitting the polygon if necessary
                #sub_polygons = split_wrapping_polygon(poly)

                # Check if any part of the polygon intersects with the bounding box
                #for sub_poly in sub_polygons:
                #    if sub_poly.intersects(bbox):
                #        selected_polygons.append(poly)  # Append the original polygon
                #        selected_ids.append(id_)
                #        break
                
                if poly.intersects(bbox):
                    selected_polygons.append(poly)  # Append the original polygon
                    selected_ids.append(id_)
                    
            return selected_polygons, selected_ids

        # Create polygons for each tile in tbl1 and tbl2
        self.tbl_RIS = ascii.read(self.tile_path)
        RIS_polygons = create_polygons(self.tbl_RIS)
        
        # Lists to store the results
        overlap_indices = []  # Indices of polygons that overlap
        innermost_indices = []  # Indices of the innermost polygons for each coordinate
        
        # Iterate through the target coordinates (list_ra and list_dec)
        for ra, dec in zip(list_ra, list_dec):
            target_point = Point(ra, dec)  # Create a Point object for the current coordinate
            max_distance = -float('inf')  # Initialize the maximum distance to the boundary as negative infinity
            innermost_index = None  # To track the index of the innermost polygon

            for i, ris_poly in enumerate(RIS_polygons):
                # Check if the target point is within the current polygon
                if ris_poly.contains(target_point):
                    overlap_indices.append(i)

                    # Calculate the distance from the point to the polygon boundary
                    distance_to_boundary = target_point.distance(ris_poly.boundary)

                    # Update the maximum distance and innermost tile index
                    if distance_to_boundary > max_distance:
                        max_distance = distance_to_boundary
                        innermost_index = i

            # Add the innermost polygon index for this point
            if innermost_index is not None:
                innermost_indices.append(innermost_index)

        if visualize:
            RIS_tilenames = self.tbl_RIS['id']
            # Create subplots
            n_coords = len(list_ra)  # Number of coordinates
            cols = visualize_ncols  # Number of columns in the subplot grid
            rows = (n_coords + cols - 1) // cols  # Calculate the required number of rows

            fig, axes = plt.subplots(rows, cols, figsize=(15, rows * 5), subplot_kw={'aspect': 'equal'})
            axes = axes.flatten()

            # Plot each coordinate and surrounding polygons
            for i, (ra, dec) in enumerate(zip(list_ra, list_dec)):
                ax = axes[i]
                
                # Center point and buffer for clipping
                center_point = Point(ra, dec)
                
                # Select polygons within the 2-degree radius (no clipping)
                selected_polygons, selected_ids = select_polygons_within_bbox(RIS_polygons, RIS_tilenames, center_point, radius=2)
                
                # Plot selected polygons
                for poly, tile_name in zip(selected_polygons, selected_ids):
                    x, y = poly.exterior.xy
                    ax.plot(x, y, color='blue', lw=1)
                    ax.fill(x, y, color='blue', alpha=0.3)
                    
                    # Calculate the centroid of the polygon
                    centroid = poly.centroid
                    
                    # Check if the centroid is within the plot boundaries
                    if ra - 2 <= centroid.x <= ra + 2 and dec - 2 <= centroid.y <= dec + 2:
                        # Add text only if the centroid is within bounds
                        ax.text(
                            centroid.x, centroid.y,  # Use the centroid coordinates for the text position
                            tile_name,
                            color='black',
                            fontsize=10,
                            ha='center',
                            va='center',
                            bbox=dict(facecolor='white', alpha=0.7, edgecolor='none')
                        )
                # Plot selected polygon
                selected_poly = RIS_polygons[innermost_indices[i]]
                selected_tilename = RIS_tilenames[innermost_indices[i]]
                selected_centroid = selected_poly.centroid
                ax.text(
                    selected_centroid.x, selected_centroid.y,  # Use the centroid coordinates for the text position
                    selected_tilename,
                    color='black',
                    fontsize=10,
                    ha='center',
                    va='center',
                    bbox=dict(facecolor='red', alpha=0.7, edgecolor='none')
                )
                
                # Plot target point
                ax.scatter(ra, dec, color='red', marker='o', s=50, label=f'Target ({ra:.2f}, {dec:.2f})')
                
                # Customize subplot
                ax.set_xlim(ra - 2, ra + 2)
                ax.set_ylim(dec - 2, dec + 2)
                ax.set_xlabel('RA')
                ax.set_ylabel('Dec')
                ax.set_title(f'Target {i+1}: ({ra:.2f}, {dec:.2f})')
                ax.legend(loc='upper left')

            # Remove unused subplots if any
            for j in range(n_coords, len(axes)):
                fig.delaxes(axes[j])

            # Adjust layout
            plt.tight_layout()
            plt.show()

        return self.tbl_RIS[innermost_indices]
# %%

T = Tiles()
list_ra = [10,20,30,40,50,50,50]
list_dec = [-45,-40,-50,-40,-60,-60,-60]
T.find_overlapping_tiles(list_ra, list_dec)
# %%
