import argparse
import numpy as np
from pyproj import Transformer


def load_geoid_grid(path: str):
    """Load geoid correction grid from ASCII file.

    The grid file must contain latitude, longitude and geoid undulation N
    on each line, expressed in WGS84 (degrees and metres). Lines beginning
    with ``#`` are ignored. The nodes are assumed to form a regular grid.
    """
    try:
        data = np.loadtxt(path, comments="#")
    except ValueError:
        data = np.loadtxt(path, delimiter=",", comments="#")

    lats = np.unique(data[:, 0])
    lons = np.unique(data[:, 1])
    lats.sort()
    lons.sort()

    lat_to_idx = {lat: i for i, lat in enumerate(lats)}
    lon_to_idx = {lon: j for j, lon in enumerate(lons)}

    grid = np.empty((len(lats), len(lons)))
    for lat, lon, n in data:
        i = lat_to_idx[lat]
        j = lon_to_idx[lon]
        grid[i, j] = n

    return lats, lons, grid


def bilinear_interpolate(lat, lon, lats, lons, grid):
    """Bilinearly interpolate geoid height at given latitude and longitude."""
    if lat < lats[0] or lat > lats[-1] or lon < lons[0] or lon > lons[-1]:
        raise ValueError("Point outside grid bounds")

    i = np.searchsorted(lats, lat) - 1
    j = np.searchsorted(lons, lon) - 1

    i = np.clip(i, 0, len(lats) - 2)
    j = np.clip(j, 0, len(lons) - 2)

    lat1, lat2 = lats[i], lats[i + 1]
    lon1, lon2 = lons[j], lons[j + 1]

    q11 = grid[i, j]
    q12 = grid[i, j + 1]
    q21 = grid[i + 1, j]
    q22 = grid[i + 1, j + 1]

    t = (lat - lat1) / (lat2 - lat1)
    u = (lon - lon1) / (lon2 - lon1)

    return (1 - t) * ((1 - u) * q11 + u * q12) + t * ((1 - u) * q21 + u * q22)


def lambert72_to_wgs84(x, y):
    transformer = Transformer.from_crs("EPSG:31370", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(x, y)
    return lat, lon


def convert_height(x, y, h, grid_path):
    lats, lons, grid = load_geoid_grid(grid_path)
    lat, lon = lambert72_to_wgs84(x, y)
    n = bilinear_interpolate(lat, lon, lats, lons, grid)
    return h - n


def main():
    parser = argparse.ArgumentParser(
        description="Convert Lambert 72 ellipsoidal heights to orthometric heights"
    )
    parser.add_argument("x", type=float, help="Lambert 72 X coordinate (m)")
    parser.add_argument("y", type=float, help="Lambert 72 Y coordinate (m)")
    parser.add_argument("h", type=float, help="Ellipsoidal height (m)")
    parser.add_argument(
        "--grid",
        default="hBG18.dat",
        help="Path to geoid grid file (default: hBG18.dat)",
    )
    args = parser.parse_args()

    H = convert_height(args.x, args.y, args.h, args.grid)
    print(f"Orthometric height: {H:.3f} m")


if __name__ == "__main__":
    main()
