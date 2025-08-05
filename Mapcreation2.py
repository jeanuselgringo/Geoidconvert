import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt

# 1. Détecte le chemin du script et construit le chemin vers le CSV
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, "HGB18.csv")

# 2. Charger le CSV (UTF-8, séparateur ;)
df = pd.read_csv(csv_path, encoding="utf-8", sep=';')

# 2. Créer la géométrie Point et GeoDataFrame en WGS84
geometry = [Point(xy) for xy in zip(df["X_WGS84"], df["Y_WGS84"])]
gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

# 3. Première carte en WGS84
fig, ax = plt.subplots(figsize=(10, 8))
gdf.plot(
    ax=ax,
    column="N",
    cmap="viridis",
    legend=True,
    markersize=25,
    alpha=0.8
)
ax.set_title("Points HGB18 — Décalage géoïde (N) en WGS84")
ax.set_xlabel("Longitude (°)")
ax.set_ylabel("Latitude (°)")
plt.tight_layout()

# 4. Reprojection en Lambert 72 (EPSG:31370)
gdf_l72 = gdf.to_crs(epsg=31370)

# 5. Deuxième carte en Lambert 72
fig, ax = plt.subplots(figsize=(10, 8))
gdf_l72.plot(
    ax=ax,
    column="N",
    cmap="viridis",
    legend=True,
    markersize=25,
    alpha=0.8
)
ax.set_title("Points HGB18 — Décalage géoïde (N) en Lambert 72")
ax.set_xlabel("X (m, EPSG:31370)")
ax.set_ylabel("Y (m, EPSG:31370)")
plt.tight_layout()
plt.show()