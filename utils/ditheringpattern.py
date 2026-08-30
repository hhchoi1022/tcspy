#%%
from astropy.coordinates import SkyCoord
from astropy import units as u
import numpy as np


def generate_dithering_offsets(n_points : int,
                               offset_arcsec : float):
    """Generate an outward spiral dithering pattern as on-sky offsets.

    The pattern is a 5x5 outward spiral (25 unique positions including the
    center). When n_points exceeds 25, the pattern repeats from the center.

    Parameters
    ----------
    n_points : int
        Number of dithering positions to generate.
    offset_arcsec : float
        Spacing between adjacent dithering positions in arcseconds.

    Returns
    -------
    offsets : list of (dx, dy) tuples
        On-sky offsets in arcseconds relative to the pattern center.
        The first position is always (0, 0).
    """
    max_points = 25  # 5x5 grid including center
    directions = [(1, 0), (0, -1), (-1, 0), (0, 1)]  # Up, Right, Down, Left
    pattern = [(0, 0)]  # Start at the center (offsets in arcsec)
    visited = set(pattern)

    direction_index = 0  # Start moving up
    steps_in_current_direction = 0
    steps_in_direction_limit = 1  # Moves per direction before turning

    for _ in range(max_points - 1):
        dx, dy = directions[direction_index]
        next_position = (pattern[-1][0] + dx * offset_arcsec, pattern[-1][1] + dy * offset_arcsec)

        # If the position is already visited, move up instead
        if next_position in visited:
            next_position = (pattern[-1][0], pattern[-1][1] + offset_arcsec)

        pattern.append(next_position)
        visited.add(next_position)

        # Update step counter
        steps_in_current_direction += 1

        # Change direction after completing steps in current limit
        if steps_in_current_direction == steps_in_direction_limit:
            direction_index = (direction_index + 1) % 4  # Rotate clockwise
            steps_in_current_direction = 0

            # Increase step size after completing up/down movements
            if direction_index in [0, 2]:
                steps_in_direction_limit += 1

    # If n_points exceeds max_points, restart the sequence
    full_pattern = pattern * ((n_points // max_points) + 1)
    return full_pattern[:n_points]


def generate_dithering_pattern(ra_center, dec_center, n_points, offset_arcsec):
    """Generate an outward spiral dithering pattern in RA/Dec coordinates.

    Same spiral as generate_dithering_offsets, converted to absolute RA/Dec
    coordinates around (ra_center, dec_center) with the RA offset corrected
    for declination.
    """
    offsets = generate_dithering_offsets(n_points = n_points, offset_arcsec = offset_arcsec)

    # Convert arcsec offsets to RA/Dec coordinates
    dithering_coords = []
    ra_center = ra_center * u.deg
    dec_center = dec_center * u.deg

    for dx, dy in offsets:
        # Convert arcsec offset to degrees
        ra_offset = dx / 3600.0 / np.cos(dec_center.to(u.rad))  # Adjust for declination
        dec_offset = dy / 3600.0
        coord = SkyCoord(ra=ra_center + ra_offset * u.deg, dec=dec_center + dec_offset * u.deg)
        dithering_coords.append((coord.ra.deg, coord.dec.deg))

    return np.array(dithering_coords)


# %%
if __name__ == '__main__':
    import matplotlib.pyplot as plt

    # Define new parameters for high declination case
    ra_center = 150.0  # in degrees
    dec_center = 87.0  # in degrees (high declination case)
    n_points = 25  # Number of dithering points
    offset_arcsec = 15  # Offset in arcseconds

    # Generate dithering pattern
    dithering_pattern = generate_dithering_pattern(ra_center, dec_center, n_points, offset_arcsec)

    # Convert RA offsets to arcseconds for better readability in visualization
    ra_offsets_arcsec = (dithering_pattern[:, 0] - ra_center) * 3600 * np.cos(np.radians(dec_center))
    dec_offsets_arcsec = (dithering_pattern[:, 1] - dec_center) * 3600

    # Visualization with axis labels in arcseconds
    plt.figure(figsize=(6, 6))
    plt.plot(ra_offsets_arcsec, dec_offsets_arcsec, marker="o", linestyle="-", label="Dithering Pattern")
    plt.scatter(0, 0, color="red", label="Center", zorder=3)

    plt.grid(True, linestyle="--", alpha=0.5)
    plt.xlabel("RA Offset (arcsec)")
    plt.ylabel("Dec Offset (arcsec)")
    plt.title("5x5 Outward Spiral Dithering Pattern (RA/Dec Offsets)")
    plt.legend()

    # Adjust ticks to show arcsecond scale
    x_ticks_arcsec = np.arange(min(ra_offsets_arcsec), max(ra_offsets_arcsec) + 1, step=offset_arcsec)
    y_ticks_arcsec = np.arange(min(dec_offsets_arcsec), max(dec_offsets_arcsec) + 1, step=offset_arcsec)
    plt.xticks(x_ticks_arcsec, [f"{x:.1f}" for x in x_ticks_arcsec])
    plt.yticks(y_ticks_arcsec, [f"{y:.1f}" for y in y_ticks_arcsec])

    plt.show()
# %%
