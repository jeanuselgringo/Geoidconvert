import os
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from scipy.interpolate import griddata

# ─── 1) Chargement de la grille HGB18 ─────────────────────────
script_dir = os.path.dirname(os.path.abspath(__file__))
grid_path  = os.path.join(script_dir, "HGB18.csv")
grid_df    = pd.read_csv(grid_path, sep=';', encoding='utf-8')
grid_geom  = [Point(x,y) for x,y in zip(grid_df.X_WGS84, grid_df.Y_WGS84)]
grid_gdf   = gpd.GeoDataFrame(grid_df, geometry=grid_geom, crs="EPSG:4326")

points_gdf = None

# ─── Traitements ──────────────────────────────────────────────
def load_points():
    global points_gdf
    f = filedialog.askopenfilename(
        filetypes=[("Shapefiles", "*.shp"),("CSV", "*.csv")],
        title="Sélectionnez vos sondages"
    )
    if not f:
        return
    try:
        if f.lower().endswith('.shp'):
            points_gdf = gpd.read_file(f)
            if points_gdf.crs is None:
                points_gdf.set_crs(epsg=4326, inplace=True)
            else:
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
        log_box.insert('end', f"• {len(points_gdf)} points chargés\n")

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

    configs = [
        ("Global WGS84", grid_gdf, points_gdf, (gx0,gx1,gy0,gy1)),
        ("Global L72",   grid_gdf.to_crs(31370), points_gdf.to_crs(31370), None),
        ("Zoom WGS84",   grid_gdf, points_gdf, (px0,px1,py0,py1)),
        ("Zoom L72",     grid_gdf.to_crs(31370), points_gdf.to_crs(31370), None),
    ]
    for title, gdf, pdf, bbox in configs:
        fig, ax = plt.subplots(figsize=(6,5))
        gdf.plot(ax=ax, column='N', cmap='viridis', markersize=4, alpha=0.5)
        pdf.plot(ax=ax, column='H_ortho', cmap='coolwarm', markersize=20, edgecolor='k')
        ax.set_title(title)
        if bbox:
            ax.set_xlim(bbox[0],bbox[1]); ax.set_ylim(bbox[2],bbox[3])
    plt.tight_layout()
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
    # SHP L72
    points_gdf.to_crs(31370).to_file(os.path.join(od,"points_corriges_L72.shp"),
                                      driver="ESRI Shapefile")
    raster_btn.config(state='normal')
    log_box.insert('end', f"• Exporté dans {od}\n")

# ─── 3) Construction IHM ─────────────────────────────────────────────────
root = tk.Tk()
root.title("Conversion d'altitudes")
root.geometry("420x360")
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

raster_btn = ttk.Button(frm, text="🌐 Créer Raster",     command=lambda: messagebox.showinfo("Info","Raster OK"), state='disabled')
raster_btn.grid(row=4, column=0, columnspan=2, pady=8, sticky='ew')

# journal
ttk.Label(frm, text="Journal des actions :").grid(row=5, column=0, columnspan=2, sticky='w')
log_box = tk.Text(frm, height=6, background='#f9f9f9', borderwidth=1, relief='solid')
log_box.grid(row=6, column=0, columnspan=2, sticky='nsew', pady=(5,0))
frm.rowconfigure(6, weight=1)

root.mainloop()