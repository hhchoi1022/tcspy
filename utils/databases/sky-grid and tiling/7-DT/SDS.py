#%%
import numpy as np
import matplotlib.pyplot as plt
from astropy.io import ascii
import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.wcs import WCS
from astropy.visualization.wcsaxes import WCSAxes

# from glob import glob
# from astropy.io import fits
# from astropy.table import Table
# from astropy import coordinates as coords
# import healpy as hp
# from matplotlib.patches import Circle
# from astropy.coordinates import Angle
# from scipy.spatial import ConvexHull
# from shapely.geometry import Polygon, Point
#%%

def path_set():
    import sys
    from pathlib import Path

    path_thisfile = Path().resolve()
    path_src = path_thisfile.parent  # absolute path of dhutil
    path_root = path_src.parent  # parent of dhutil
    if path_root not in map(Path, sys.path):
        sys.path.append(str(path_root))
    return path_src


def get_tiles(indices, center=False):
    path_src = path_set()
    if center:
        center = ascii.read(str(path_src / "displaycenter.txt"))
        # center = ascii.read("/Users/dhhyun/VSCode/7DT/displaycenter.txt")
        return center[indices]
    vertices = ascii.read(str(path_src / "displayfootprint.txt"))
    # vertices = ascii.read("/Users/dhhyun/VSCode/7DT/displayfootprint.txt")
    return vertices[indices]


# # Legacy Ver.
# def overlay_tiles(**kwargs_tile):  # _fig, **kwargs_plot):
#     """
#     Legacy Ver.
#     USE WCS PROJECTION AT THE POLES (and RA ~ 0)

#     # Note for future update
#     # Handle single or multiple axes
#     if isinstance(ax, np.ndarray):
#         # If ax is an array of axes, loop through each and plot on each axis
#         for axis in ax.flat:
#             _plot_on_axis(axis, ra, dec, center, polygon, kwargs_plot)
#     else:
#         # If ax is a single axis, plot directly on it
#         _plot_on_axis(ax, ra, dec, center, polygon, kwargs_plot)
#     """

#     # Tile kwargs
#     kwargs = {
#         "color": "orange",  #'C0' if tile%2==0 else 'orange',
#         "lw": 0.5,
#     }

#     # Label kwargs
#     kwargs_tile.setdefault("fontsize", 4)
#     kwargs_tile.setdefault("color", "red")

#     path_src = path_set()
#     center = ascii.read(str(path_src / "displaycenter.txt"))
#     vertices = ascii.read(str(path_src / "displayfootprint.txt"))

#     # Get RA/Dec range from current axis limits
#     ax = plt.gca()
#     # fig = plt.gcf()
#     xlim = ax.get_xlim()  # Pixel limits on x-axis
#     ylim = ax.get_ylim()  # Pixel limits on y-axis

#     # Check if the WCS projection is being used
#     is_wcs = isinstance(ax, WCSAxes)
#     if is_wcs:
#         transf = ax.get_transform("world")
#         kwargs["transform"] = transf
#         kwargs_tile["transform"] = transf
#         # mind the inverted ra axis!
#         bottom_left = ax.wcs.pixel_to_world(xlim[0], ylim[0])
#         bottom_right = ax.wcs.pixel_to_world(xlim[1], ylim[0])
#         top_left = ax.wcs.pixel_to_world(xlim[0], ylim[1])
#         top_right = ax.wcs.pixel_to_world(xlim[1], ylim[1])
#         # from astropy.wcs.utils import pixel_to_skycoord
#         # pixel_to_skycoord(xlim[0], ylim[0], ax.wcs)  # another option

#         rau, ral = (bottom_left.ra.deg, top_right.ra.deg)
#         decl, decu = (bottom_left.dec.deg, top_right.dec.deg)

#         ralims = [
#             bottom_left.ra.deg,
#             bottom_right.ra.deg,
#             top_right.ra.deg,
#             top_left.ra.deg,
#         ]
#         declims = [
#             bottom_left.dec.deg,
#             bottom_right.dec.deg,
#             top_right.dec.deg,
#             top_left.dec.deg,
#         ]
#         pole = (
#             True
#             if (np.abs(ralims[0] - ralims[1]) > 75)
#             & (np.abs(ralims[1] - ralims[2]) > 75)
#             else False
#         )
#         wrap = False if bottom_left.ra.deg > top_right.ra.deg else True
#         # redundant ideas
#         # pole = True if np.prod(np.roll(ralims, 1) - ralims) < 0 else False
#         # pole = True if (ralims[1] - ralims[0]) * (ralims[3] - ralims[2]) < 0 else False
#         # wrap = True if np.max(ralims) - np.min(ralims) >= 180 else False
#     else:
#         ral, rau = xlim
#         decl, decu = ylim
#         pole = True  # Conservative choice
#         wrap = True if xlim[0] < 0 < xlim[1] else False


#     margin_deg = 2
#     margin_pix = 30

#     # Iterate over all available tiles
#     for tile in range(len(vertices)):
#         # different linestyles for even/odd tiles
#         kwargs["alpha"] = 1  # if tile%2==0 else 0
#         kwargs["ls"] = "dotted" if tile % 2 == 0 else "dashed"

#         ras = vertices[tile][0::2]  # in deg
#         decs = vertices[tile][1::2]
#         ra = center["ra"][tile]
#         dec = center["dec"][tile]

#         # Pre-select relevant tiles as world_to_pixel is expensive
#         if is_wcs:
#             if pole:
#                 # Assuming Southern Hemisphere
#                 deccut = np.max(declims)
#                 if dec > deccut:
#                     continue
#             else:
#                 if wrap:
#                     inside_ra = (ral + margin_deg < ra) | (ra < rau - margin_deg)
#                 else:
#                     inside_ra = (ral - margin_deg < ra) & (ra < rau + margin_deg)
#                 inside_dec = (decl - margin_deg < dec) & (dec < decu + margin_deg)
#                 if not inside_ra and not inside_dec:
#                     continue
#         else:
#             if pole:
#                 deccut = decu
#                 if dec > deccut:
#                     continue
#             else:
#                 if wrap:
#                     inside_ra = (ral + margin_deg < ra) | (ra < rau - margin_deg)
#                 else:
#                     inside_ra = (ral - margin_deg < ra) & (ra < rau + margin_deg)
#                 inside_dec = (decl - margin_deg < dec) & (dec < decu + margin_deg)
#                 if not inside_ra and not inside_dec:
#                     continue

#         # Determine if the tile is in the figure
#         if is_wcs:
#             x, y = ax.wcs.world_to_pixel(SkyCoord(ra, dec, unit="deg"))
#             inside_fig = xlim[0] < x < xlim[1] and ylim[0] < y < ylim[1]
#         else:
#             x, y = ra, dec
#             inside_fig = xlim[0] < x < xlim[1] and ylim[0] < y < ylim[1]

#         # outside = 0
#         # for x, y in zip(ras, decs):
#         #     if not xlim[0] + margin_pix < x < xlim[1] - margin_pix:
#         #         outside += 1
#         #     if not ylim[0] + margin_pix < y < ylim[1] - margin_pix:
#         #         outside += 1

#         # inside_fig_strict = not bool(outside)
#         inside_fig_strict = (
#             xlim[0] + margin_pix < x < xlim[1] - margin_pix
#             and ylim[0] + margin_pix < y < ylim[1] - margin_pix
#         )

#         # Plot tiles
#         if inside_fig:
#             ras = ras + (ras[0],)  # 4 + 1 points for a closed loop
#             decs = decs + (decs[0],)
#             ax.plot(ras, decs, **kwargs)
#         # Plot labels
#         if inside_fig_strict:
#             ax.text(ra, dec, f"T{tile:05}", ha="center", va="center", **kwargs_tile)


def overlay_tiles(**kwargs_tile):  # _fig, **kwargs_plot):
    """
    USE WCS PROJECTION AT THE POLES (and RA ~ 0)

    set kwargs to control the tile style
    set kwargs_tile to control the label style

    # Note for future update
    # Handle single or multiple axes
    if isinstance(ax, np.ndarray):
        # If ax is an array of axes, loop through each and plot on each axis
        for axis in ax.flat:
            _plot_on_axis(axis, ra, dec, center, polygon, kwargs_plot)
    else:
        # If ax is a single axis, plot directly on it
        _plot_on_axis(ax, ra, dec, center, polygon, kwargs_plot)
    """

    # Tile kwargs
    kwargs = {
        "color": "orange",  #'C0' if tile%2==0 else 'orange',
        "lw": 0.5,
        "clip_on": True,  # does nothing!
    }

    # Label kwargs
    kwargs_tile.setdefault("fontsize", 4)
    kwargs_tile.setdefault("color", "red")

    path_src = path_set()
    center = ascii.read(str(path_src / "displaycenter.txt"))
    vertices = ascii.read(str(path_src / "displayfootprint.txt"))

    # Get RA/Dec range from current axis limits
    ax = plt.gca()
    # fig = plt.gcf()
    xlim = ax.get_xlim()  # Pixel limits on x-axis
    ylim = ax.get_ylim()  # Pixel limits on y-axis

    # Check if the WCS projection is being used
    is_wcs = isinstance(ax, WCSAxes)
    if is_wcs:
        transf = ax.get_transform("world")
        kwargs["transform"] = transf
        kwargs_tile["transform"] = transf
        # mind the inverted ra axis!
        bottom_left = ax.wcs.pixel_to_world(xlim[0], ylim[0])
        bottom_right = ax.wcs.pixel_to_world(xlim[1], ylim[0])
        top_left = ax.wcs.pixel_to_world(xlim[0], ylim[1])
        top_right = ax.wcs.pixel_to_world(xlim[1], ylim[1])
        # from astropy.wcs.utils import pixel_to_skycoord
        # pixel_to_skycoord(xlim[0], ylim[0], ax.wcs)  # another option

        rau, ral = (bottom_left.ra.deg, top_right.ra.deg)
        decl, decu = (bottom_left.dec.deg, top_right.dec.deg)

        ralims = [
            bottom_left.ra.deg,
            bottom_right.ra.deg,
            top_right.ra.deg,
            top_left.ra.deg,
        ]
        declims = [
            bottom_left.dec.deg,
            bottom_right.dec.deg,
            top_right.dec.deg,
            top_left.dec.deg,
        ]
        pole = (
            True
            if (np.abs(ralims[0] - ralims[1]) > 75)
            & (np.abs(ralims[1] - ralims[2]) > 75)
            else False
        )
        wrap = False if bottom_left.ra.deg > top_right.ra.deg else True
        # redundant ideas
        # pole = True if np.prod(np.roll(ralims, 1) - ralims) < 0 else False
        # pole = True if (ralims[1] - ralims[0]) * (ralims[3] - ralims[2]) < 0 else False
        # wrap = True if np.max(ralims) - np.min(ralims) >= 180 else False

        margin_deg = 2
        margin_pix = 50  # 30

        # Iterate over all available tiles
        for tile in range(len(vertices)):
            # different linestyles for even/odd tiles
            kwargs["alpha"] = 1  # if tile%2==0 else 0
            kwargs["ls"] = "dotted" if tile % 2 == 0 else "dashed"

            ras = vertices[tile][0::2]  # in deg
            decs = vertices[tile][1::2]
            ra = center["ra"][tile]
            dec = center["dec"][tile]

            # Pre-select relevant tiles as world_to_pixel is expensive
            if pole:
                # Assuming Southern Hemisphere
                deccut = np.max(declims)
                if dec > deccut:
                    continue
            else:
                if wrap:
                    inside_ra = (ral + margin_deg < ra) | (ra < rau - margin_deg)
                else:
                    inside_ra = (ral - margin_deg < ra) & (ra < rau + margin_deg)
                inside_dec = (decl - margin_deg < dec) & (dec < decu + margin_deg)
                if not inside_ra and not inside_dec:
                    continue

            # Determine if the tile is in the figure
            x, y = ax.wcs.world_to_pixel(SkyCoord(ra, dec, unit="deg"))
            inside_fig = xlim[0] < x < xlim[1] and ylim[0] < y < ylim[1]

            # Faster ver.
            inside_fig_strict = (
                xlim[0] + margin_pix < x < xlim[1] - margin_pix
                and ylim[0] + margin_pix < y < ylim[1] - margin_pix
            )

            # # Slower: checks if tiles are fully inside
            # outside = 0
            # for x, y in zip(ras, decs):
            #     x, y = ax.wcs.world_to_pixel(SkyCoord(ra, dec, unit="deg"))
            #     if not xlim[0] + margin_pix < x < xlim[1] - margin_pix:
            #         outside += 1
            #     if not ylim[0] + margin_pix < y < ylim[1] - margin_pix:
            #         outside += 1
            # inside_fig_strict = not bool(outside)

            # Plot tiles
            if inside_fig:
                ras = ras + (ras[0],)  # 4 + 1 points for a closed loop
                decs = decs + (decs[0],)
                ax.plot(ras, decs, **kwargs)
            # Plot labels
            if inside_fig_strict:
                ax.text(ra, dec, f"T{tile:05}", ha="center", va="center", **kwargs_tile)

    # without wcs projection
    else:
        ral, rau = xlim
        decl, decu = ylim
        wrap = True if xlim[0] < 0 < xlim[1] else False

        margin_deg = 2
        margin_pix = 0.1

        # Iterate over all available tiles
        for tile in range(len(vertices)):
            # different linestyles for even/odd tiles
            kwargs["alpha"] = 1  # if tile%2==0 else 0
            kwargs["ls"] = "dotted" if tile % 2 == 0 else "dashed"

            ras = vertices[tile][0::2]  # in deg
            decs = vertices[tile][1::2]
            ra = center["ra"][tile]
            dec = center["dec"][tile]
            if wrap:
                ras = np.array(ras) - (np.array(ras) > 180).astype("int") * 360
                ra = ra - 360 if ra > 180 else ra

            if tile == 10770:
                print(tile, inside_fig_strict, ras)

            # Pre-select relevant tiles as world_to_pixel is expensive
            if wrap:
                inside_ra = (ral + margin_deg < ra) | (ra < rau - margin_deg)
            else:
                inside_ra = (ral - margin_deg < ra) & (ra < rau + margin_deg)
            inside_dec = (decl - margin_deg < dec) & (dec < decu + margin_deg)
            if not inside_ra and not inside_dec:
                continue

            # Determine if the tile is in the figure
            x, y = ra, dec
            inside_fig = xlim[0] < x < xlim[1] and ylim[0] < y < ylim[1]

            # # only take tiles when they're fully inside
            # outside = 0
            # for x, y in zip(ras, decs):
            #     if not xlim[0] + margin_pix < x < xlim[1] - margin_pix:
            #         outside += 1
            #     if not ylim[0] + margin_pix < y < ylim[1] - margin_pix:
            #         outside += 1
            # inside_fig_strict = not bool(outside)
            inside_fig_strict = inside_fig

            # Plot tiles
            if inside_fig:
                ras = list(ras) + [ras[0]]  # 4 + 1 points for a closed loop
                decs = list(decs) + [decs[0]]
                ax.plot(ras, decs, **kwargs)
            # Plot labels
            if inside_fig_strict:
                ax.text(ra, dec, f"T{tile:05}", ha="center", va="center", **kwargs_tile)


def set_xylim(ax, xl, xu, yl, yu):
    """Useful when the wcs projection is used"""
    # inverted ra axis taken into account
    bottom_left = ax.wcs.world_to_pixel(SkyCoord(xu, yl, unit="deg"))
    top_right = ax.wcs.world_to_pixel(SkyCoord(xl, yu, unit="deg"))
    # print(ax.get_xlim(), ax.get_ylim())
    # print(bottom_left, top_right)
    ax.set_xlim(bottom_left[0], top_right[0])
    ax.set_ylim(bottom_left[1], top_right[1])
    return bottom_left[0], top_right[0], bottom_left[1], top_right[1]


# %%

# Example with No WCS Projection
if __name__ == "__main__":
    plt.figure(dpi=300)
    ax = plt.axes()
    ax.plot([110, 120], [-25, -30])
    ax.grid()
    ax.set_ylim(-35, -22)
    overlay_tiles()

if __name__ == "__main__":
    plt.figure(dpi=300)
    ax = plt.axes()
    # ax.plot([358, 2], [-25, -30])
    ax.plot([-2, 2], [-25, -30])
    ax.grid()
    ax.set_xlim(-4, 4)
    # ax.set_ylim(-35, -22)
    overlay_tiles(fontsize=10)
# %%

# With Manual WCS Projection
if __name__ == "__main__":
    wcs = WCS(naxis=2)
    wcs.wcs.crval = [115, -27.0]  # Center of the projection in RA/Dec (degrees)
    wcs.wcs.cdelt = [-0.01, 0.01]  # Pixel scale in degrees/pixel
    wcs.wcs.crpix = [100, 100]  # Reference pixel (center of the plot)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]  # Gnomonic (tangent plane) projection

    plt.figure(dpi=300)
    ax = plt.subplot(projection=wcs)
    # fig, ax = plt.subplots(subplot_kw={"projection": wcs}, dpi=300)
    ax.plot([110, 120], [-25, -30], "o--", transform=ax.get_transform("world"))
    ax.grid()
    ax.coords[0].set_format_unit(u.deg)  # ra axis unit hour to deg

    set_xylim(ax, 108, 123, -34, -21)
    overlay_tiles(color="k", fontsize=6.6)


# %%

# With ligo.skymap "astro zoom" wcs projection
if __name__ == "__main__":
    import ligo.skymap.plot  # CAREFUL: works behind the scene

    plt.figure(dpi=300)
    ax = plt.axes(
        projection="astro zoom", center="7.7h -27d", radius="8 deg"
    )  # , rotate='20 deg')
    ax.plot([110, 120], [-25, -30], "o--", transform=ax.get_transform("world"))
    ax.grid()
    ax.coords[0].set_format_unit(u.deg)  # ra axis unit hour to deg

    set_xylim(ax, 108, 123, -34, -21)
    overlay_tiles(color="b", fontweight="bold")

# %%

# when ra ~= 0
if __name__ == "__main__":
    import ligo.skymap.plot  # CAREFUL: works behind the scene

    plt.figure(dpi=300)
    ax = plt.axes(projection="astro zoom", center="0h 0d", radius="8 deg")
    ra = get_tiles(18885)[0::2]
    ra = ra + (ra[0],)
    dec = get_tiles(18885)[1::2]
    dec = dec + (dec[0],)
    ax.plot(ra, dec, transform=ax.get_transform("world"))
    ax.grid()
    ax.coords[0].set_format_unit(u.deg)  # ra axis unit hour to deg

    set_xylim(ax, 355, 5, -5, 5)
    overlay_tiles(color="b", fontweight="bold")

# %%

if __name__ == "__main__":
    import ligo.skymap.plot  # CAREFUL: works behind the scene

    plt.figure(dpi=300)
    ax = plt.axes(projection="astro zoom", center="0h -88d", radius="8 deg")
    vertices = get_tiles(0)
    ax.plot(vertices[0::2], vertices[1::2], "ro", transform=ax.get_transform("world"))
    # ax.plot([0], [-89], "ro", transform=ax.get_transform("world"))
    ax.grid()
    ax.coords[0].set_format_unit(u.deg)  # ra axis unit hour to deg

    # set_xylim(ax, 355, 5, -5, 5)
    overlay_tiles(color="b", fontweight="bold")

# %%
