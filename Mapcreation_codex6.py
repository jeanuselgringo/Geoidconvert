import os
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from scipy.interpolate import griddata
import rasterio
from rasterio.transform import from_origin
import folium
import webbrowser

# ─── 1) Chargement de la grille HGB18 ─────────────────────────
script_dir = os.path.dirname(os.path.abspath(__file__))
grid_path  = os.path.join(script_dir, "HGB18.csv")
grid_df    = pd.read_csv(grid_path, sep=';', encoding='utf-8')
grid_geom  = [Point(x,y) for x,y in zip(grid_df.X_WGS84, grid_df.Y_WGS84)]
grid_gdf   = gpd.GeoDataFrame(grid_df, geometry=grid_geom, crs="EPSG:4326")

points_gdf = None
points_crs_original = None

# ─── Traitements ──────────────────────────────────────────────
def load_points():
    global points_gdf, points_crs_original
    f = filedialog.askopenfilename(
        filetypes=[("Shapefiles", "*.shp"),("CSV", "*.csv")],
        title="Sélectionnez vos sondages"
    )
    if not f:
        return
    try:
        if f.lower().endswith('.shp'):
            points_gdf = gpd.read_file(f)
            points_crs_original = points_gdf.crs
            if points_gdf.crs is None:
                messagebox.showwarning("Attention", "CRS non défini. Supposition WGS84.")
                points_gdf.set_crs(epsg=4326, inplace=True)
            points_gdf = points_gdf.to_crs(epsg=4326)
        else:
            df = pd.read_csv(f, sep=';', encoding='utf-8')
            if not {"X_WGS84","Y_WGS84"}.issubset(df.columns):
                raise ValueError("CSV: colonnes X_WGS84 & Y_WGS84 requises")
            points_gdf = gpd.GeoDataFrame(
                df,
                geometry=[Point(x,y) for x,y in zip(df.X_WGS84, df.Y_WGS84)],
                crs="EPSG:4326"
            )
            points_crs_original = points_gdf.crs

        # MAJ menu altitude
        nums = points_gdf.select_dtypes(include='number').columns.tolist()
        if not nums:
            raise ValueError("Aucun champ numérique trouvé")
        alt_var.set(nums[0])
        menu = alt_menu['menu']
        menu.delete(0,'end')
        for c in nums:
            menu.add_command(label=c, command=lambda v=c: alt_var.set(v))

        plot_btn.config(state='normal')
        export_btn.config(state='disabled')
        crs_msg = points_crs_original.to_string() if points_crs_original else "inconnu"
        log_box.insert('end', f"• {len(points_gdf)} points chargés (CRS initial : {crs_msg})\n")

    except Exception as e:
        messagebox.showerror("Erreur", str(e))
        log_box.insert('end', f"✗ Erreur de chargement : {e}\n")
        points_gdf = None
        plot_btn.config(state='disabled')

def interpolate_and_compute():
    grid_xy = np.vstack((grid_gdf.geometry.x, grid_gdf.geometry.y)).T
    vals    = grid_gdf['N'].values
    pts_xy  = np.vstack((points_gdf.geometry.x, points_gdf.geometry.y)).T
    Ni      = griddata(grid_xy, vals, pts_xy, method='linear')
    mask    = np.isnan(Ni)
    if mask.any():
        Ni[mask] = griddata(grid_xy, vals, pts_xy[mask], method='nearest')
    points_gdf['N_interp'] = Ni
    fld = alt_var.get()
    points_gdf['H_ortho']  = points_gdf[fld] - Ni

def plot_maps():
    if points_gdf is None:
        return
    interpolate_and_compute()
    # bornes général/zoom
    gx0,gy0,gx1,gy1 = grid_gdf.total_bounds
    px0,py0,px1,py1 = points_gdf.total_bounds
    lpx0,lpy0,lpx1,lpy1 = points_gdf.to_crs(31370).total_bounds

    configs = [
        ("Global WGS84", grid_gdf, points_gdf, (gx0,gx1,gy0,gy1)),
        ("Global L72",   grid_gdf.to_crs(31370), points_gdf.to_crs(31370), None),
        ("Zoom WGS84",   grid_gdf, points_gdf, (px0,px1,py0,py1)),
        ("Zoom L72",     grid_gdf.to_crs(31370), points_gdf.to_crs(31370), (lpx0,lpx1,lpy0,lpy1)),
    ]
    for title, gdf, pdf, bbox in configs:
        fig, ax = plt.subplots(figsize=(6,5))
        # réserver de l'espace à droite et en bas pour les barres de couleurs
        fig.subplots_adjust(right=0.85, bottom=0.2)
        gdf.plot(ax=ax, column='N', cmap='viridis', markersize=4, alpha=0.5)
        pdf.plot(ax=ax, column='H_ortho', cmap='coolwarm', markersize=20, edgecolor='k')
        sm1 = cm.ScalarMappable(
            cmap='viridis',
            norm=colors.Normalize(vmin=gdf['N'].min(), vmax=gdf['N'].max())
        )
        sm1._A = []
        # barre de couleur verticale pour la grille N
        cbar1 = fig.colorbar(sm1, ax=ax, fraction=0.035, pad=0.02)
        cbar1.set_label('N (m)')
        sm2 = cm.ScalarMappable(
            cmap='coolwarm',
            norm=colors.Normalize(vmin=pdf['H_ortho'].min(), vmax=pdf['H_ortho'].max())
        )
        sm2._A = []
        # barre de couleur horizontale pour H_ortho afin d'éviter le chevauchement
        cbar2 = fig.colorbar(
            sm2,
            ax=ax,
            orientation='horizontal',
            fraction=0.035,
            pad=0.12
        )
        cbar2.set_label('H_ortho (m)')
        ax.set_title(title)
        epsg = gdf.crs.to_epsg() if gdf.crs else None
        if epsg == 4326:
            ax.set_xlabel("Longitude (°)")
            ax.set_ylabel("Latitude (°)")
        else:
            ax.set_xlabel("X (m)")
            ax.set_ylabel("Y (m)")
        if bbox:
            ax.set_xlim(bbox[0],bbox[1]); ax.set_ylim(bbox[2],bbox[3])
        # ajuste la mise en page pour chaque figure afin d'éviter le chevauchement
        fig.tight_layout()
    plt.show()
    export_btn.config(state='normal')
    log_box.insert('end', "• Cartes affichées\n")

def export_data():
    if points_gdf is None:
        return
    interpolate_and_compute()
    od = os.path.join(script_dir,"ConversionExport")
    os.makedirs(od, exist_ok=True)
    # CSV
    points_gdf.drop(columns='geometry').to_csv(os.path.join(od,"points_corriges.csv"),
                                               sep=';',index=False)
    # SHP WGS84
    points_gdf.to_file(os.path.join(od,"points_corriges_WGS84.shp"),
                       driver="ESRI Shapefile")
    # SHP L72
    points_gdf.to_crs(31370).to_file(os.path.join(od,"points_corriges_L72.shp"),
                                     driver="ESRI Shapefile")
    raster_btn.config(state='normal')
    folium_btn.config(state='normal')
    log_box.insert('end', f"• Exporté dans {od}\n")

def create_raster():
    try:
        gdf_l72 = grid_gdf.to_crs(31370)
        xs = gdf_l72.geometry.x.values
        ys = gdf_l72.geometry.y.values
        zs = gdf_l72["N"].values
        pixel_size = 10
        # choix de l'étendue : grille complète ou zone des sondages
        if raster_extent_var.get() == "Sondages" and points_gdf is not None:
            bounds = points_gdf.to_crs(31370).total_bounds
        else:
            bounds = gdf_l72.total_bounds
        xmin, ymin, xmax, ymax = bounds
        width  = int(np.ceil((xmax - xmin) / pixel_size))
        height = int(np.ceil((ymax - ymin) / pixel_size))
        xi = np.linspace(xmin, xmin + width * pixel_size, width)
        yi = np.linspace(ymax - height * pixel_size, ymax, height)
        XI, YI = np.meshgrid(xi, yi)
        ZI = griddata((xs, ys), zs, (XI, YI), method='linear')
        mask = np.isnan(ZI)
        if mask.any():
            ZI[mask] = griddata((xs, ys), zs, (XI[mask], YI[mask]), method='nearest')
        transform = from_origin(xmin, ymax, pixel_size, pixel_size)
        out_dir = os.path.join(script_dir, "ConversionExport")
        os.makedirs(out_dir, exist_ok=True)
        out_tif = os.path.join(out_dir, "HGB18_interpolated.tif")
        with rasterio.open(
            out_tif, 'w',
            driver='GTiff',
            height=height,
            width=width,
            count=1,
            dtype=ZI.dtype,
            crs='EPSG:31370',
            transform=transform,
            nodata=-9999
        ) as dst:
            dst.write(ZI, 1)
        messagebox.showinfo("Succès", f"Raster créé : {out_tif}")
        log_box.insert('end', f"• Raster créé → {out_tif}\n")
    except Exception as e:
        messagebox.showerror("Erreur", str(e))
        log_box.insert('end', f"✗ Erreur raster : {e}\n")

def create_folium_map():
    if points_gdf is None:
        return
    try:
        if 'N_interp' not in points_gdf.columns or 'H_ortho' not in points_gdf.columns:
            interpolate_and_compute()
        gdf_wgs = points_gdf.to_crs(4326)
        fld = alt_var.get()
        centre = [gdf_wgs.geometry.y.mean(), gdf_wgs.geometry.x.mean()]
        m = folium.Map(location=centre, zoom_start=12, tiles="OpenStreetMap")
        folium.raster_layers.WmsTileLayer(
            url="https://wxs.ign.fr/choisirgeoportail/geoportail/wms",
            layers="GEOGRAPHICALGRIDSYSTEMS.PLANIGN",
            fmt="image/png",
            transparent=True,
            name="Plan IGN"
        ).add_to(m)
        for idx, row in gdf_wgs.iterrows():
            popup_html = (
                f"<b>ID :</b> {idx}<br>"
                f"<b>Alt. ellipsoïdale :</b> {row[fld]:.2f} m<br>"
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
        out_dir = os.path.join(script_dir, "ConversionExport")
        os.makedirs(out_dir, exist_ok=True)
        out_html = os.path.join(out_dir, "points_interactifs.html")
        m.save(out_html)
        webbrowser.open(out_html)
        log_box.insert('end', f"• Carte interactive → {out_html}\n")
    except Exception as e:
        messagebox.showerror("Erreur", str(e))
        log_box.insert('end', f"✗ Erreur Folium : {e}\n")

# ─── 3) Construction IHM ─────────────────────────────────────────────────
root = tk.Tk()
root.title("Conversion d'altitudes")
root.geometry("420x420")
style = ttk.Style(root)
style.theme_use('clam')

frm = ttk.Frame(root, padding=15)
frm.pack(fill='both', expand=True)

# grille 2 colonnes
for i in (0,1):
    frm.columnconfigure(i, weight=1)

load_btn = ttk.Button(frm, text="📂 Charger sondages", command=load_points)
load_btn.grid(row=0, column=0, columnspan=2, pady=(0,10), sticky='ew')

ttk.Label(frm, text="Champ altitude :").grid(row=1, column=0, sticky='e')
alt_var = tk.StringVar()
alt_menu = ttk.OptionMenu(frm, alt_var, "")
alt_menu.grid(row=1, column=1, sticky='ew', padx=(5,0))

plot_btn   = ttk.Button(frm, text="🗺️ Afficher cartes",  command=plot_maps,   state='disabled')
plot_btn.grid(row=2, column=0, columnspan=2, pady=8, sticky='ew')

export_btn = ttk.Button(frm, text="💾 Export données",    command=export_data, state='disabled')
export_btn.grid(row=3, column=0, columnspan=2, pady=8, sticky='ew')

ttk.Label(frm, text="Étendue raster :").grid(row=4, column=0, sticky='e')
raster_extent_var = tk.StringVar(value="Grille HGB18")
raster_extent_menu = ttk.OptionMenu(frm, raster_extent_var, "Grille HGB18", "Grille HGB18", "Sondages")
raster_extent_menu.grid(row=4, column=1, sticky='ew', padx=(5,0))

raster_btn = ttk.Button(frm, text="🌐 Créer Raster",     command=create_raster, state='disabled')
raster_btn.grid(row=5, column=0, columnspan=2, pady=8, sticky='ew')

folium_btn = ttk.Button(frm, text="🌍 Carte interactive", command=create_folium_map, state='disabled')
folium_btn.grid(row=6, column=0, columnspan=2, pady=8, sticky='ew')

# journal
ttk.Label(frm, text="Journal des actions :").grid(row=7, column=0, columnspan=2, sticky='w')
log_box = tk.Text(frm, height=6, background='#f9f9f9', borderwidth=1, relief='solid')
log_box.grid(row=8, column=0, columnspan=2, sticky='nsew', pady=(5,0))
frm.rowconfigure(8, weight=1)

root.mainloop()
