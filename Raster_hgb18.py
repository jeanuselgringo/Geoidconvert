import os
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from scipy.interpolate import griddata
import rasterio
from rasterio.transform import from_origin

# 1) Paramètres
script_dir = os.path.dirname(os.path.abspath(__file__))
grid_csv   = os.path.join(script_dir, "HGB18.csv")
out_tif    = os.path.join(script_dir, "HGB18_interpolated.tif")

# 2) Charge la grille HBG18
df = pd.read_csv(grid_csv, sep=';', encoding='utf-8')
geometry = [Point(xy) for xy in zip(df["X_WGS84"], df["Y_WGS84"])]
gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

# 3) Projette en Lambert72 pour avoir des unités métriques régulières
gdf_l72 = gdf.to_crs(epsg=31370)

# 4) Coordonnées et valeurs
xs = gdf_l72.geometry.x.values
ys = gdf_l72.geometry.y.values
zs = gdf_l72["N"].values

# 5) Définition de la grille raster
# Choisissez la résolution (en mètres)
pixel_size = 10  # par exemple 100 m, ajustez selon besoin

xmin, ymin, xmax, ymax = gdf_l72.total_bounds
width  = int(np.ceil((xmax - xmin) / pixel_size))
height = int(np.ceil((ymax - ymin) / pixel_size))

# Grille de points où on veut interpoler
xi = np.linspace(xmin, xmin + width * pixel_size, width)
yi = np.linspace(ymax - height * pixel_size, ymax, height)
# Note : y de haut en bas pour rasterio
XI, YI = np.meshgrid(xi, yi)

# 6) Interpolation bilinéaire (linear = bilinear sur grille régulière)
ZI = griddata(
    (xs, ys), zs,
    (XI, YI),
    method="linear"
)

# 7) Fallback nearest pour les NaN à l’extérieur
mask = np.isnan(ZI)
if mask.any():
    ZI[mask] = griddata((xs, ys), zs, (XI[mask], YI[mask]), method="nearest")

# 8) Écriture du GeoTIFF
transform = from_origin(xmin, ymax, pixel_size, pixel_size)
new_crs  = 'EPSG:31370'

with rasterio.open(
    out_tif, 'w',
    driver='GTiff',
    height=height,
    width=width,
    count=1,
    dtype=ZI.dtype,
    crs=new_crs,
    transform=transform,
    nodata=-9999
) as dst:
    dst.write(ZI, 1)

print(f"Raster bilinéaire créé → {out_tif}")