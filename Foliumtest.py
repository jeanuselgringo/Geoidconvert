import os
import webbrowser
import pandas as pd
import geopandas as gpd
import folium

# 1) Détermine le dossier du script et les paths
script_dir = os.path.dirname(os.path.abspath(__file__))
export_dir = os.path.join(script_dir, "ConversionExport")
csv_path   = os.path.join(export_dir, "points_corriges.csv")
shp_path   = os.path.join(export_dir, "points_corriges_L72.shp")

# 2) Charge d'abord le Shapefile (si disponible) pour récupérer la géométrie
if os.path.exists(shp_path):
    gdf = gpd.read_file(shp_path)
    # Optionnel : si tu veux aussi les attributs du CSV à jour
    df  = pd.read_csv(csv_path, sep=';', encoding='utf-8')
    # Remplace les attributs dans gdf
    for col in df.columns:
        if col not in gdf.columns:
            gdf[col] = df[col]
else:
    # Fallback : lire les coords depuis le CSV
    df = pd.read_csv(csv_path, sep=';', encoding='utf-8')
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["X_WGS84"], df["Y_WGS84"]),
        crs="EPSG:4326"
    )

# 3) Centre de la carte
centre = [gdf.geometry.y.mean(), gdf.geometry.x.mean()]

# 4) Création de la map Folium
m = folium.Map(location=centre, zoom_start=12, tiles="OpenStreetMap")

# 5) Exemple d’ajout de fond WMS (IGN)
folium.raster_layers.WmsTileLayer(
    url="https://wxs.ign.fr/choisirgeoportail/geoportail/wms",
    layers="GEOGRAPHICALGRIDSYSTEMS.PLANIGN",
    fmt="image/png",
    transparent=True,
    name="Plan IGN"
).add_to(m)

# 6) Ajout des points avec pop-up
for idx, row in gdf.iterrows():
    popup_html = (
        f"<b>ID :</b> {idx}<br>"
        f"<b>Alt. éllo :</b> {row.get('Elevation', float('nan')):.2f} m<br>"
        f"<b>N_interp :</b> {row['N_interp']:.2f} m<br>"
        f"<b>H_ortho :</b> {row['H_ortho']:.2f} m"
    )
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=5,
        color="blue",
        fill=True,
        fill_color="cyan",
        fill_opacity=0.7,
        popup=folium.Popup(popup_html, max_width=200)
    ).add_to(m)

# 7) Sauvegarde et ouverture
out_html = os.path.join(export_dir, "points_interactifs.html")
os.makedirs(export_dir, exist_ok=True)
m.save(out_html)
print("Carte interactive créée →", out_html)
webbrowser.open(out_html)
