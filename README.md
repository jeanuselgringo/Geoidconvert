# Geoidconvert

Script to convert Lambert 72 ellipsoidal heights to orthometric heights using a geoid correction grid (e.g. hBG18). The grid file must contain WGS84 latitude, longitude and geoid undulation `N` for each node.

## Usage

```bash
python geoidconvert.py <X> <Y> <h> --grid hBG18.dat
```

- `X`, `Y` — Lambert 72 coordinates in metres.
- `h` — ellipsoidal height in metres.
- `--grid` — path to geoid grid (defaults to `hBG18.dat` in the working directory).
- Output is the orthometric height in metres.

Example with sample coordinates and the provided `hBG18.dat` grid:

```bash
python geoidconvert.py 178264.755 148044.476 182.088
```

The script requires the `numpy` and `pyproj` packages.
