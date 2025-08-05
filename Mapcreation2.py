import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog

# Chargement de la grille de conversion hBG18
script_dir = os.path.dirname(os.path.abspath(__file__))
grid_path = os.path.join(script_dir, "HGB18.csv")
grid_df = pd.read_csv(grid_path, encoding="utf-8", sep=";")
grid_geom = [Point(xy) for xy in zip(grid_df["X_WGS84"], grid_df["Y_WGS84"])]
grid_gdf = gpd.GeoDataFrame(grid_df, geometry=grid_geom, crs="EPSG:4326")

points_gdf = None


def load_points():
    """Ouvre un fichier CSV ou Shapefile et met à jour le menu des altitudes."""
    global points_gdf
    filepath = filedialog.askopenfilename(
        filetypes=[("Shapefiles", "*.shp"), ("CSV files", "*.csv")]
    )
    if not filepath:
        return

    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".shp":
        points_gdf = gpd.read_file(filepath)
        if points_gdf.crs is None:
            points_gdf.set_crs(epsg=4326, inplace=True)
        else:
            points_gdf = points_gdf.to_crs(epsg=4326)
    elif ext == ".csv":
        df = pd.read_csv(filepath)
        if not {"X_WGS84", "Y_WGS84"}.issubset(df.columns):
            raise ValueError("Le CSV doit contenir les colonnes 'X_WGS84' et 'Y_WGS84'.")
        geometry = [Point(xy) for xy in zip(df["X_WGS84"], df["Y_WGS84"])]
        points_gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    else:
        return

    numeric_cols = points_gdf.select_dtypes(include="number").columns.tolist()
    alt_var.set(numeric_cols[0] if numeric_cols else "")
    alt_menu["menu"].delete(0, "end")
    for col in numeric_cols:
        alt_menu["menu"].add_command(label=col, command=tk._setit(alt_var, col))


def plot_maps():
    """Affiche la grille et les points sur deux cartes."""
    if points_gdf is None or not alt_var.get():
        return

    fig, ax = plt.subplots(figsize=(10, 8))
    grid_gdf.plot(
        ax=ax,
        column="N",
        cmap="viridis",
        legend=True,
        markersize=5,
        alpha=0.5,
    )
    points_gdf.plot(
        ax=ax,
        column=alt_var.get(),
        cmap="coolwarm",
        legend=True,
        markersize=40,
        edgecolor="black",
    )
    ax.set_title(f"Points — {alt_var.get()} en WGS84")
    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    plt.tight_layout()

    grid_l72 = grid_gdf.to_crs(epsg=31370)
    pts_l72 = points_gdf.to_crs(epsg=31370)

    fig, ax = plt.subplots(figsize=(10, 8))
    grid_l72.plot(
        ax=ax,
        column="N",
        cmap="viridis",
        legend=True,
        markersize=5,
        alpha=0.5,
    )
    pts_l72.plot(
        ax=ax,
        column=alt_var.get(),
        cmap="coolwarm",
        legend=True,
        markersize=40,
        edgecolor="black",
    )
    ax.set_title(f"Points — {alt_var.get()} en Lambert 72")
    ax.set_xlabel("X (m, EPSG:31370)")
    ax.set_ylabel("Y (m, EPSG:31370)")
    plt.tight_layout()
    plt.show()


root = tk.Tk()
root.title("Conversion d'altitudes")

load_button = tk.Button(root, text="Ouvrir un fichier", command=load_points)
load_button.pack(pady=5)

alt_var = tk.StringVar(root)
alt_menu = tk.OptionMenu(root, alt_var, [])
alt_menu.pack(pady=5)

plot_button = tk.Button(root, text="Afficher", command=plot_maps)
plot_button.pack(pady=5)

root.mainloop()


