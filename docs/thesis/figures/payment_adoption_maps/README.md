# Mapas de adopcion de medios de pago digitales

Artefactos generados desde `scripts/figures/make_payment_adoption_maps.py`.

Fuente de datos:
- Sample: `03_models/artifacts/interannual_enriched/pooled_2024_2025-estimation-sample5pct-censo4-micro-osm-eod2012.parquet`
- Geometria: `/Volumes/KINGSTON/tesis-project/raw/zonas777/Zonas777-04-04-2014/Shape/Zonas777_V07_04_2014.shp`

Definiciones:
- `share_qr_red = n(choice_nested == 1) / n_trips`.
- `share_qr_other = n(choice_nested == 2) / n_trips`.
- `share_digital = share_qr_red + share_qr_other`.
- Zonas grises: menos de 50 viajes en la muestra.

Outputs:
- `zona777_payment_share_maps_3panel_sample5pct.png`
- `zona777_payment_share_maps_3panel_oriente_zoom_sample5pct.png`
- `zona777_bivariate_qr_red_qr_other_oriente_zoom_sample5pct.png`
- `zona777_bivariate_qr_red_qr_other_full_sample5pct.png`
- `zona777_bivariate_qr_red_edu_full_sample5pct.png`
- `zona777_share_qr_red_sample5pct.png`
- `zona777_share_qr_other_sample5pct.png`
- `zona777_share_digital_sample5pct.png`
- `zona777_payment_shares_sample5pct.csv`
