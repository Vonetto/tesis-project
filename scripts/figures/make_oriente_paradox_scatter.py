import os
from pathlib import Path
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "docs" / "thesis" / "figures" / "payment_adoption_maps"
CSV_PATH = OUT_DIR / "zona777_payment_shares_sample5pct.csv"
ZONAS777_SHP = Path("/Volumes/KINGSTON/tesis-project/raw/zonas777/Zonas777-04-04-2014/Shape/Zonas777_V07_04_2014.shp")

def main():
    if not CSV_PATH.exists():
        print(f"Error: {CSV_PATH} no existe. Ejecuta make_payment_adoption_maps.py primero.")
        return
    if not ZONAS777_SHP.exists():
        print(f"Error: {ZONAS777_SHP} no existe. Asegúrate de tener el disco externo conectado.")
        return
        
    # Cargar datos de shares
    df_shares = pd.read_csv(CSV_PATH)
    # Filtrar zonas con muy pocos viajes para mayor estabilidad visual
    df_shares = df_shares[df_shares["n_trips"] >= 50].copy()
    
    # Cargar mapeo de zonas a macrozonas
    gdf = gpd.read_file(ZONAS777_SHP)[["ZONA777", "MACROZONA"]]
    gdf["ZONA777"] = pd.to_numeric(gdf["ZONA777"], errors="coerce").astype("Int64")
    
    # Unir
    df = df_shares.merge(gdf, on="ZONA777", how="inner")
    
    # Crear variable de agrupación
    df["is_oriente"] = df["MACROZONA"].astype(str).str.upper() == "ORIENTE"
    df["Grupo"] = df["is_oriente"].map({True: "Macrozona Oriente", False: "Resto RM"})
    
    # Configurar estilo
    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(11, 7), dpi=150)
    
    # Scatter plot
    sns.scatterplot(
        data=df, 
        x="share_cine18_universitaria_o_mas_micro_z", 
        y="share_qr_red", 
        hue="Grupo", 
        style="Grupo",
        palette={"Macrozona Oriente": "#e34a33", "Resto RM": "#a6bddb"},
        alpha=0.6,
        s=60,
        ax=ax
    )
    
    # Lineas de tendencia
    sns.regplot(
        data=df[df["is_oriente"]], 
        x="share_cine18_universitaria_o_mas_micro_z", 
        y="share_qr_red", 
        scatter=False, 
        color="#e34a33", 
        ax=ax,
        label="Tendencia Oriente",
        line_kws={"linewidth": 2.5, "linestyle": "--"}
    )
    sns.regplot(
        data=df[~df["is_oriente"]], 
        x="share_cine18_universitaria_o_mas_micro_z", 
        y="share_qr_red", 
        scatter=False, 
        color="#2b8cbe", 
        ax=ax,
        label="Tendencia Resto RM",
        line_kws={"linewidth": 2.5}
    )
    
    # Estética
    ax.set_title("La Paradoja de Oriente: Adopción Bruta vs. Condicional", fontsize=15, fontweight="bold", pad=20)
    ax.set_xlabel("Capital Educativo (Z-score Proporción Universitaria)", fontsize=12)
    ax.set_ylabel("Share de adopción QR_RED (%)", fontsize=12)
    
    # Formatear eje Y como porcentaje si los datos están en 0-1
    if df["share_qr_red"].max() <= 1.0:
        import matplotlib.ticker as mtick
        ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))

    # Caja de texto explicativa
    text = (
        "¿Por qué el coeficiente de Oriente es NEGATIVO?\n\n"
        "1. Oriente tiene los valores más altos de Educación (eje X).\n"
        "2. Por eso tiene mucha adopción 'bruta' (puntos arriba a la derecha).\n"
        "3. Pero nota que la línea de puntos (Oriente) está POR DEBAJO\n"
        "   de la línea sólida (Resto RM).\n\n"
        "Conclusión: A IGUAL nivel educativo, vivir en Oriente \n"
        "reduce la probabilidad de usar QR_RED respecto al resto de la ciudad."
    )
    ax.text(
        0.02, 0.96, text, transform=ax.transAxes, fontsize=10, 
        verticalalignment='top', 
        bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.9, edgecolor="#cccccc")
    )
    
    ax.legend(title="Ubicación Geográfica", loc="lower right", frameon=True)
    
    out_path = OUT_DIR / "scatter_oriente_paradox_qr_red.png"
    fig.savefig(out_path, bbox_inches="tight")
    print(f"✅ Gráfico guardado en: {out_path}")

if __name__ == "__main__":
    main()
