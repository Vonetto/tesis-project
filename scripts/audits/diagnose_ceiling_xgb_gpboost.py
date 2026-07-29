"""Diagnóstico de techo predictivo a nivel id_tarjeta con XGBoost y GPBoost.

Mide cuánta señal hay en la matriz supervisada para separar:
  - BINARIO:    BIP vs QR   (QR = QR_RED + QR_OTHER)
  - MULTICLASE: BIP / QR_OTHER / QR_RED

DECISIONES METODOLÓGICAS (revisión 2026-05-30):

1. FUENTE DE FEATURES (--feature-source):
   - "contract" (DEFAULT): unión de los feature_sets del JSON del builder.
     Comparable con logit_main/ml_wide. Es el universo que de verdad comen
     los modelos. Respeta el contrato del builder.
   - "all_numeric": todas las columnas numéricas menos IDs/target/metadata.
     Techo bruto (upper bound), NO comparable con los sets del JSON.
   Las coordenadas de origen (origin_top1/top2 lon/lat) se garantizan dentro
   en ambos modos porque son la sensibilidad espacial pedida.

2. COMPARACIÓN GPBoost: el aporte del término espacial GP se aísla corriendo,
   sobre LA MISMA submuestra y LAS MISMAS folds, tres modelos:
     - xgb_subsample      (XGBoost, sin GP)
     - gpb_boost_only     (GPBoost boosting, sin GP)
     - gpb_gp_spatial     (GPBoost boosting + Gaussian Process espacial)
   El delta gpb_gp_spatial - gpb_boost_only aísla el GP; el contraste con
   xgb_subsample sitúa a GPBoost frente al booster de referencia.

3. COORDENADAS DEL GP: el componente Gaussian Process SIEMPRE usa coordenadas
   en UTM 19S (metros), independiente de --coords-utm, porque el kernel Matérn
   opera sobre distancias y lon/lat en grados no es isotrópico (~17% de
   distorsión en Santiago). --coords-utm solo afecta las coords como FEATURES
   del árbol (donde la proyección casi no cambia el AUC).

4. SPLIT (--split):
   - "random" (DEFAULT): StratifiedKFold por fila = por tarjeta. Es un UPPER
     BOUND: tarjetas espacialmente vecinas caen en train y test, así que
     sobreestima la señal espacial (el GP interpola en vez de extrapolar).
   - "grouped": GroupKFold por origin_zone_top1. Mide generalización a zonas
     no vistas. El gap random - grouped indica cuánta señal es "ubicación
     memorizada" vs estructura generalizable.

5. MÉTRICAS multiclase: balanced accuracy, macro-F1, ROC-AUC OvR y además
   PR-AUC (average precision) OvR por clase, más informativa para QR_RED
   (2,16% del universo).

REQUIERE (instalar en larch-env):  pip install xgboost gpboost

Uso típico:
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
      scripts/audits/diagnose_ceiling_xgb_gpboost.py \
      --scope interannual_ml --variant clean --home-filter alta --min-trips 3

Flags:
  --feature-source {contract,all_numeric}   default contract
  --split {random,grouped}                   default random
  --min-home-trips N      sensibilidad: n_home_dest_trips_card>=N
  --coords-utm            coords (features del árbol) a UTM 19S
  --gp-sample N           submuestra GPBoost (default 250000)
  --gp-rounds N           boosting rounds GPBoost (default 300)
  --gp-num-neighbors N    vecinos Vecchia del GP espacial (default 30)
  --gp-num-threads N      threads GPBoost (default 1; evita deadlocks en macOS)
  --xgb-sample N          submuestra XGBoost full (default: sin submuestra)
  --xgb-n-estimators N    nº árboles XGBoost (default 500)
  --quick                 atajo: xgb_sample=200000, n_estimators=150, skip_ablation
  --skip-gpboost          solo XGBoost
  --skip-ablation         solo full y no_cohort
  --gp-binary-only        GPBoost solo binario (sin OvR multiclase)

Outputs: tmp/audits/user_level_redesign/ceiling_xgb_gpboost_*_<suffix>.csv
  donde <suffix> codifica scope/variant/home/n, fuente de features, split y coords.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold, StratifiedKFold

PROJECT_ROOT = Path(__file__).resolve().parents[2]
USER_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign"

N_SPLITS = 5
RANDOM_STATE = 42

# Coordenadas de origen pedidas como features ML (garantizadas en ambos modos).
COORD_FEATURES = ["origin_top1_lon", "origin_top1_lat",
                  "origin_top2_lon", "origin_top2_lat"]
# El componente GP usa SOLO estas, y SIEMPRE en UTM (ver punto 3).
GP_COORD_COLS = ["origin_top1_lon", "origin_top1_lat"]
# Columna de agrupación para split espacial.
GROUP_COL = "origin_zone_top1"

ID_TARGET = {"id_tarjeta", "tipo_tarjeta", "is_qr", "is_qr_red",
             "is_qr_other", "target_conflict_flag"}
ID_ZONES = {"zona_hogar", "origin_zone_top1", "activity_zone_top1",
            "home_confidence"}
METADATA_NOT_FEATURE = {"n_home_dest_trips_card", "home_zone_top_share"}

# Redundancias exactas (r=±1): se excluyen SOLO en all_numeric. En contract se
# respeta el JSON (que ya las contiene); para árboles r=1 no rompe nada y la
# comparabilidad con ml_wide manda. Para logit se documentó el drop aparte.
DROP_REDUNDANT_ALL_NUMERIC = {
    "coarse_route_has_early_late_rcs",
    "service_within_od_variability_weighted",
    "offer_origin_metro_like_share",
}

COHORT_EXACT = {"share_trips_2025", "share_trips_2024", "first_trip_year",
                "last_trip_year", "trip_span_days", "recent_majority_2025",
                "solo_2025"}

UTM_COORD_PAIRS = [("origin_top1_lon", "origin_top1_lat"),
                   ("origin_top2_lon", "origin_top2_lat")]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# --------------------------------------------------------------------------
def universe_suffix(scope, variant, home_filter, min_trips, min_home_trips):
    suffix = f"{scope}_{variant}_{home_filter}_n{min_trips}"
    if min_home_trips > 0:
        suffix += f"_home{min_home_trips}"
    return suffix


def matrix_path(scope, variant, home_filter, min_trips, min_home_trips):
    return USER_DIR / f"user_model_matrix_{universe_suffix(scope, variant, home_filter, min_trips, min_home_trips)}.parquet"


def feature_sets_path(scope, variant, home_filter, min_trips, min_home_trips):
    return USER_DIR / f"user_model_matrix_feature_sets_{universe_suffix(scope, variant, home_filter, min_trips, min_home_trips)}.json"


def reproject_lonlat_to_utm(lon: np.ndarray, lat: np.ndarray):
    """(lon, lat) grados EPSG:4326 -> (x, y) metros UTM 19S EPSG:32719.
    Preserva NaN."""
    from pyproj import Transformer
    tr = Transformer.from_crs("EPSG:4326", "EPSG:32719", always_xy=True)
    mask = ~(np.isnan(lon) | np.isnan(lat))
    x = np.full_like(lon, np.nan, dtype=np.float64)
    y = np.full_like(lat, np.nan, dtype=np.float64)
    if mask.any():
        xv, yv = tr.transform(lon[mask], lat[mask])
        x[mask] = xv
        y[mask] = yv
    return x, y


def reproject_coords_to_utm(df: pl.DataFrame) -> pl.DataFrame:
    """Reproyecta los pares lon/lat (features del árbol) a UTM 19S, in-place
    sobre los mismos nombres de columna."""
    out = df
    for lon_col, lat_col in UTM_COORD_PAIRS:
        if lon_col not in df.columns or lat_col not in df.columns:
            print(f"  ⚠️ par {lon_col}/{lat_col} ausente; se omite.")
            continue
        x, y = reproject_lonlat_to_utm(
            df[lon_col].to_numpy().astype(np.float64),
            df[lat_col].to_numpy().astype(np.float64),
        )
        out = out.with_columns([pl.Series(lon_col, x), pl.Series(lat_col, y)])
    print("  ✅ coords (features) reproyectadas a UTM 19S (metros).")
    return out


def classify_families(feature_cols: list[str]) -> dict[str, list[str]]:
    fam = {k: [] for k in ["cohort", "use", "geo", "socio", "osm", "route",
                           "offer", "bip", "hybrid", "other"]}
    for c in feature_cols:
        if c in COHORT_EXACT:
            fam["cohort"].append(c)
        elif "_bip_load_" in c:
            fam["bip"].append(c)
        elif c.startswith("res_"):
            fam["socio"].append(c)
        elif "_osm_" in c:
            fam["osm"].append(c)
        elif c.startswith("offer_"):
            fam["offer"].append(c)
        elif c.startswith(("service_route", "coarse_route", "service_within_od",
                            "share_trips_in_multi_route_od", "top_od_service")):
            fam["route"].append(c)
        elif c.startswith("hyb_"):
            fam["hybrid"].append(c)
        elif (c.startswith(("home_macro_", "origin_top1_macro_", "origin_top2_macro_",
                            "dest_top1_macro_", "activity_top1_macro_", "activity_top2_macro_"))
              or c.endswith(("_lon", "_lat")) or "_zone_top" in c
              or c.endswith("_zone_entropy")):
            fam["geo"].append(c)
        elif c.startswith(("hora_", "share_lab_", "share_no_lab", "share_trips_",
                           "n_trasbordos", "t_vehiculo_", "t_espera_", "n_viajes",
                           "n_dias_activos", "n_semanas_activas")):
            fam["use"].append(c)
        else:
            fam["other"].append(c)
    return fam


def load_matrix(scope, variant, home_filter, min_trips, min_home_trips):
    mpath = matrix_path(scope, variant, home_filter, min_trips, min_home_trips)
    if not mpath.exists():
        raise FileNotFoundError(f"No existe matriz: {mpath}\n¿KINGSTON montado?")
    df = pl.read_parquet(mpath)
    print(f"Matriz: {df.height:,} filas, {len(df.columns)} cols")
    return df


def features_from_contract(df, scope, variant, home_filter, min_trips, min_home_trips) -> list[str]:
    """Unión de los feature_sets del JSON del builder, intersectada con
    columnas numéricas presentes. Comparable con logit_main/ml_wide."""
    fpath = feature_sets_path(scope, variant, home_filter, min_trips, min_home_trips)
    if not fpath.exists():
        raise FileNotFoundError(
            f"No existe JSON de feature-sets: {fpath}\n"
            "Necesario para --feature-source contract.")
    payload = json.loads(fpath.read_text())
    union = []
    for feats in payload.get("feature_sets", {}).values():
        union.extend(feats)
    union = list(dict.fromkeys(union))  # dedupe preservando orden
    cols = set(df.columns)
    present = [c for c in union if c in cols and df[c].dtype.is_numeric()]
    missing = [c for c in union if c not in cols]
    if missing:
        print(f"  ⚠️ {len(missing)} features del JSON no están en la matriz: {missing}")
    return present


def features_all_numeric(df) -> list[str]:
    cols = set(df.columns)
    return sorted(
        c for c in cols
        if c not in ID_TARGET and c not in ID_ZONES
        and c not in METADATA_NOT_FEATURE and c not in DROP_REDUNDANT_ALL_NUMERIC
        and df[c].dtype.is_numeric()
    )


def make_features(df, source, scope, variant, home_filter, min_trips, min_home_trips):
    if source == "contract":
        feats = features_from_contract(df, scope, variant, home_filter, min_trips, min_home_trips)
    else:
        feats = features_all_numeric(df)
    # Garantizar coords de origen en ambos modos (sensibilidad espacial pedida).
    for c in COORD_FEATURES:
        if c not in feats and c in df.columns and df[c].dtype.is_numeric():
            feats.append(c)
    feats = list(dict.fromkeys(feats))
    fam = classify_families(feats)
    return feats, fam


def make_targets(df: pl.DataFrame):
    tt = df["tipo_tarjeta"].to_numpy()
    y_bin = np.where(tt == "BIP", 0, 1).astype(int)
    mmap = {"BIP": 0, "QR_OTHER": 1, "QR_RED": 2}
    y_multi = np.array([mmap[v] for v in tt], dtype=int)
    return y_bin, y_multi


def make_folds(split, y_strat, groups, n_splits=N_SPLITS, seed=RANDOM_STATE):
    """Devuelve lista de (train_idx, test_idx). Folds COMPARTIDAS entre
    modelos para que las comparaciones sean limpias."""
    if split == "grouped":
        if groups is None:
            raise ValueError("split=grouped requiere groups (origin_zone_top1).")
        gkf = GroupKFold(n_splits=n_splits)
        return list(gkf.split(np.zeros(len(y_strat)), y_strat, groups))
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    return list(skf.split(np.zeros(len(y_strat)), y_strat))


# --------------------------------------------------------------------------
# Núcleos de entrenamiento (reciben folds explícitas)
# --------------------------------------------------------------------------
def xgb_binary_oof(X, y, folds, n_estimators):
    import xgboost as xgb
    oof = np.zeros(len(y))
    for tr, te in folds:
        clf = xgb.XGBClassifier(objective="binary:logistic", eval_metric="logloss",
                                n_estimators=n_estimators, learning_rate=0.05,
                                max_depth=6, subsample=0.8, colsample_bytree=0.8,
                                reg_lambda=1.0, tree_method="hist", n_jobs=-1,
                                random_state=RANDOM_STATE)
        clf.fit(X[tr], y[tr])
        oof[te] = clf.predict_proba(X[te])[:, 1]
    return {"auc": roc_auc_score(y, oof), "pr_auc": average_precision_score(y, oof),
            "base_rate": float(y.mean())}


def xgb_multi_oof(X, y, folds, n_estimators):
    import xgboost as xgb
    proba = np.zeros((len(y), 3))
    for tr, te in folds:
        clf = xgb.XGBClassifier(objective="multi:softprob", num_class=3,
                                eval_metric="mlogloss", n_estimators=n_estimators,
                                learning_rate=0.05, max_depth=6, subsample=0.8,
                                colsample_bytree=0.8, reg_lambda=1.0,
                                tree_method="hist", n_jobs=-1, random_state=RANDOM_STATE)
        clf.fit(X[tr], y[tr])
        proba[te] = clf.predict_proba(X[te])
    return multiclass_metrics(y, proba)


def multiclass_metrics(y, proba) -> dict:
    pred = proba.argmax(1)
    out = {"balanced_accuracy": balanced_accuracy_score(y, pred),
           "macro_f1": f1_score(y, pred, average="macro"),
           "auc_macro_ovr": roc_auc_score(y, proba, multi_class="ovr", average="macro")}
    for c, n in [(0, "BIP"), (1, "QR_OTHER"), (2, "QR_RED")]:
        yb = (y == c).astype(int)
        out[f"auc_ovr_{n}"] = roc_auc_score(yb, proba[:, c])
        out[f"ap_ovr_{n}"] = average_precision_score(yb, proba[:, c])  # PR-AUC
        out[f"base_{n}"] = float(yb.mean())
    return out


# --------------------------------------------------------------------------
# XGBoost sobre dataset completo (o submuestra), con ablación
# --------------------------------------------------------------------------
def run_xgboost_full(df, feats, fam, y_bin, y_multi, groups, args):
    # Submuestra opcional para iterar rápido.
    if args.xgb_sample and df.height > args.xgb_sample:
        idx = stratified_subsample(df, y_multi, args.xgb_sample)
        dX = df[idx]
        yb, ym = y_bin[idx], y_multi[idx]
        grp = groups[idx] if groups is not None else None
        print(f"\n[XGB] submuestra: {len(idx):,} filas")
    else:
        dX, yb, ym, grp = df, y_bin, y_multi, groups

    X_full = dX.select(feats).to_numpy().astype(np.float64)
    idxmap = {c: i for i, c in enumerate(feats)}
    folds_b = make_folds(args.split, yb, grp)
    folds_m = make_folds(args.split, ym, grp)

    runs = {"full": feats, "no_cohort": [c for c in feats if c not in COHORT_EXACT]}
    if not args.skip_ablation:
        for famname in ["use", "geo", "socio", "osm", "route", "offer", "bip",
                        "hybrid", "cohort"]:
            drop = set(fam[famname])
            if drop:
                runs[f"drop_{famname}"] = [c for c in feats if c not in drop]

    rows_b, rows_m = [], []
    for name, rfeats in runs.items():
        Xr = X_full[:, [idxmap[c] for c in rfeats]]
        print(f"\n[XGB] {name} ({len(rfeats)} feats)")
        rb = {"model": "xgboost", "run": name, "n_features": len(rfeats),
              "n_rows": len(yb), **xgb_binary_oof(Xr, yb, folds_b, args.xgb_n_estimators)}
        rows_b.append(rb)
        print(f"  binario AUC={rb['auc']:.4f} PR-AUC={rb['pr_auc']:.4f}")
        rm = {"model": "xgboost", "run": name, "n_features": len(rfeats),
              "n_rows": len(ym), **xgb_multi_oof(Xr, ym, folds_m, args.xgb_n_estimators)}
        rows_m.append(rm)
        print(f"  multi balAcc={rm['balanced_accuracy']:.4f} AUCmacro={rm['auc_macro_ovr']:.4f}")
        print(f"    AUC OvR  BIP={rm['auc_ovr_BIP']:.3f} QR_OTHER={rm['auc_ovr_QR_OTHER']:.3f} "
              f"QR_RED={rm['auc_ovr_QR_RED']:.3f}")
        print(f"    PR-AUC   BIP={rm['ap_ovr_BIP']:.3f} QR_OTHER={rm['ap_ovr_QR_OTHER']:.3f} "
              f"QR_RED={rm['ap_ovr_QR_RED']:.3f} (base QR_RED={rm['base_QR_RED']:.3f})")
    return rows_b, rows_m


# --------------------------------------------------------------------------
# GPBoost (submuestra) + XGBoost en LA MISMA submuestra/folds
# --------------------------------------------------------------------------
def _impute_median_fold(Xtr, Xte):
    med = np.nanmedian(Xtr, axis=0)
    med = np.where(np.isnan(med), 0.0, med)
    return np.where(np.isnan(Xtr), med, Xtr), np.where(np.isnan(Xte), med, Xte)


def gpboost_binary_oof(
    X,
    coords,
    y,
    folds,
    use_gp,
    *,
    n_rounds=300,
    num_neighbors=30,
    num_threads=1,
    label="gpboost",
):
    import gpboost as gpb
    oof = np.zeros(len(y))
    for fold_idx, (tr, te) in enumerate(folds, start=1):
        t0 = time.perf_counter()
        log(
            f"{label}: fold {fold_idx}/{len(folds)} start "
            f"(train={len(tr):,}, test={len(te):,}, rounds={n_rounds}, use_gp={use_gp})"
        )
        Xtr, Xte = _impute_median_fold(X[tr], X[te])
        log(f"{label}: fold {fold_idx} imputation ok ({time.perf_counter() - t0:.1f}s)")
        params = {
            "objective": "binary",
            "learning_rate": 0.05,
            "max_depth": 6,
            "verbose": 0,
            "num_leaves": 63,
            # GPBoost/LightGBM puede quedarse colgado en autodeteccion
            # multithread en macOS. Estos flags hacen el entrenamiento
            # deterministico y evitan el deadlock observado en smoke tests.
            "num_threads": num_threads,
            "force_col_wise": True,
        }
        if use_gp:
            log(f"{label}: fold {fold_idx} building GPModel (num_neighbors={num_neighbors})")
            gp_model = gpb.GPModel(gp_coords=coords[tr], cov_function="matern",
                                   cov_fct_shape=1.5, likelihood="bernoulli_logit",
                                   gp_approx="vecchia",
                                   num_neighbors=num_neighbors)
            log(f"{label}: fold {fold_idx} training GPBoost+GP")
            booster = gpb.train(params=params, train_set=gpb.Dataset(Xtr, label=y[tr]),
                                gp_model=gp_model, num_boost_round=n_rounds,
                                verbose_eval=False)
            log(f"{label}: fold {fold_idx} predicting GPBoost+GP")
            pred = booster.predict(data=Xte, gp_coords_pred=coords[te],
                                   predict_var=False, pred_latent=False)
            oof[te] = pred["response_mean"]
        else:
            log(f"{label}: fold {fold_idx} training GPBoost boost-only")
            booster = gpb.train(params=params, train_set=gpb.Dataset(Xtr, label=y[tr]),
                                num_boost_round=n_rounds, verbose_eval=False)
            log(f"{label}: fold {fold_idx} predicting GPBoost boost-only")
            oof[te] = booster.predict(data=Xte)
        log(f"{label}: fold {fold_idx}/{len(folds)} done ({time.perf_counter() - t0:.1f}s)")
    return {"auc": roc_auc_score(y, oof), "pr_auc": average_precision_score(y, oof),
            "base_rate": float(y.mean())}


def stratified_subsample(df, y_multi, n, seed=RANDOM_STATE):
    rng = np.random.default_rng(seed)
    if df.height <= n:
        return np.arange(df.height)
    idx = []
    for cls in [0, 1, 2]:
        cls_idx = np.where(y_multi == cls)[0]
        take = min(int(round(n * len(cls_idx) / len(y_multi))), len(cls_idx))
        idx.append(rng.choice(cls_idx, size=take, replace=False))
    return np.sort(np.concatenate(idx))


def run_gpboost(df, feats, y_bin, y_multi, groups, args):
    if not all(c in df.columns for c in GP_COORD_COLS):
        print(f"⚠️ Faltan {GP_COORD_COLS}; se salta GPBoost.")
        return [], []

    sub = stratified_subsample(df, y_multi, args.gp_sample)
    print(f"\n[GPBoost] submuestra estratificada: {len(sub):,} filas")
    dsub = df[sub]
    yb, ym = y_bin[sub], y_multi[sub]
    grp = groups[sub] if groups is not None else None

    # Features del booster: todo menos las gp_coords (que van como GP).
    gp_feats = [c for c in feats if c not in set(GP_COORD_COLS)]
    X = dsub.select(gp_feats).to_numpy().astype(np.float64)

    # gp_coords SIEMPRE en UTM (punto 3), independiente de --coords-utm.
    lon = dsub[GP_COORD_COLS[0]].to_numpy().astype(np.float64)
    lat = dsub[GP_COORD_COLS[1]].to_numpy().astype(np.float64)
    if args.coords_utm:
        # En este caso las columnas YA están en UTM; usarlas tal cual.
        cx, cy = lon, lat
    else:
        cx, cy = reproject_lonlat_to_utm(lon, lat)
    coords = np.column_stack([cx, cy])
    cmed = np.nanmedian(coords, axis=0)
    coords = np.where(np.isnan(coords), cmed, coords)

    # Folds COMPARTIDAS para los 3 modelos.
    folds_b = make_folds(args.split, yb, grp)

    rows_b = []
    # 1) XGBoost en la MISMA submuestra/folds (referencia honesta).
    Xx = dsub.select(feats).to_numpy().astype(np.float64)
    print("  [xgb_subsample] binario...")
    rx = {"model": "gpboost_block", "run": "xgb_subsample", "n_features": len(feats),
          "n_rows": len(sub), **xgb_binary_oof(Xx, yb, folds_b, args.xgb_n_estimators)}
    rows_b.append(rx)
    print(f"    AUC={rx['auc']:.4f} PR-AUC={rx['pr_auc']:.4f}")
    # 2) GPBoost sin GP, 3) GPBoost con GP.
    for use_gp, tag in [(False, "gpb_boost_only"), (True, "gpb_gp_spatial")]:
        print(f"  [{tag}] binario...")
        rb = {"model": "gpboost_block", "run": tag, "n_features": len(gp_feats),
              "n_rows": len(sub), **gpboost_binary_oof(
                  X,
                  coords,
                  yb,
                  folds_b,
                  use_gp,
                  n_rounds=args.gp_rounds,
                  num_neighbors=args.gp_num_neighbors,
                  num_threads=args.gp_num_threads,
                  label=tag,
              )}
        rows_b.append(rb)
        print(f"    AUC={rb['auc']:.4f} PR-AUC={rb['pr_auc']:.4f}")

    rows_m = []
    if not args.gp_binary_only:
        for cls, cname in [(0, "BIP"), (1, "QR_OTHER"), (2, "QR_RED")]:
            yc = (ym == cls).astype(int)
            folds_c = make_folds(args.split, yc, grp)
            r = gpboost_binary_oof(
                X,
                coords,
                yc,
                folds_c,
                use_gp=True,
                n_rounds=args.gp_rounds,
                num_neighbors=args.gp_num_neighbors,
                num_threads=args.gp_num_threads,
                label=f"gpb_gp_ovr_{cname}",
            )
            rows_m.append({"model": "gpboost_block", "run": "gpb_gp_ovr",
                           "class": cname, "n_rows": len(sub), **r})
            print(f"  [gp OvR] {cname}: AUC={r['auc']:.4f} PR-AUC={r['pr_auc']:.4f}")
    return rows_b, rows_m


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", default="interannual_ml")
    ap.add_argument("--variant", default="clean")
    ap.add_argument("--home-filter", default="alta")
    ap.add_argument("--min-trips", type=int, default=3)
    ap.add_argument("--min-home-trips", type=int, default=0)
    ap.add_argument("--feature-source", choices=["contract", "all_numeric"],
                    default="contract")
    ap.add_argument("--split", choices=["random", "grouped"], default="random")
    ap.add_argument("--coords-utm", action="store_true")
    ap.add_argument("--gp-sample", type=int, default=250_000)
    ap.add_argument("--gp-rounds", type=int, default=300)
    ap.add_argument("--gp-num-neighbors", type=int, default=30)
    ap.add_argument("--gp-num-threads", type=int, default=1)
    ap.add_argument("--xgb-sample", type=int, default=0)
    ap.add_argument("--xgb-n-estimators", type=int, default=500)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--skip-gpboost", action="store_true")
    ap.add_argument("--skip-ablation", action="store_true")
    ap.add_argument("--gp-binary-only", action="store_true")
    args = ap.parse_args()

    if args.quick:
        args.xgb_sample = args.xgb_sample or 200_000
        args.xgb_n_estimators = min(args.xgb_n_estimators, 150)
        args.gp_sample = min(args.gp_sample, 50_000)
        args.gp_rounds = min(args.gp_rounds, 50)
        args.gp_binary_only = True
        args.skip_ablation = True
        print("[QUICK] xgb_sample=200k, n_estimators<=150, gp_sample<=50k, gp_rounds<=50, gp_binary_only, skip_ablation")

    df = load_matrix(args.scope, args.variant, args.home_filter, args.min_trips, args.min_home_trips)
    if args.coords_utm:
        print("\n[SENSIBILIDAD] coords (features) -> UTM 19S")
        df = reproject_coords_to_utm(df)

    feats, fam = make_features(df, args.feature_source, args.scope, args.variant,
                               args.home_filter, args.min_trips, args.min_home_trips)
    y_bin, y_multi = make_targets(df)
    groups = df[GROUP_COL].to_numpy() if (args.split == "grouped" and GROUP_COL in df.columns) else None
    if args.split == "grouped" and groups is None:
        raise ValueError(f"split=grouped pero falta {GROUP_COL} en la matriz.")

    print(f"\nfeature_source={args.feature_source}  split={args.split}  "
          f"coords={'UTM' if args.coords_utm else 'lonlat'}")
    print("Familias:", {k: len(v) for k, v in fam.items() if v})
    print(f"n_features={len(feats)}  coords presentes={[c for c in COORD_FEATURES if c in feats]}")
    if fam["other"]:
        print(f"⚠️ Sin familia: {fam['other']}")
    print(f"Binario base QR={y_bin.mean():.4f} | "
          f"BIP {np.mean(y_multi==0):.4f} QR_OTHER {np.mean(y_multi==1):.4f} QR_RED {np.mean(y_multi==2):.4f}")

    all_b, all_m, gp_b, gp_m = [], [], [], []
    xb, xm = run_xgboost_full(df, feats, fam, y_bin, y_multi, groups, args)
    all_b += xb
    all_m += xm
    if not args.skip_gpboost:
        gb, gm = run_gpboost(df, feats, y_bin, y_multi, groups, args)
        gp_b += gb
        gp_m += gm

    USER_DIR.mkdir(parents=True, exist_ok=True)
    tag = f"_{args.feature_source}_{args.split}" + ("_utm" if args.coords_utm else "")
    suffix = f"{universe_suffix(args.scope, args.variant, args.home_filter, args.min_trips, args.min_home_trips)}{tag}"
    pl.DataFrame(all_b).write_csv(USER_DIR / f"ceiling_xgb_binary_{suffix}.csv")
    pl.DataFrame(all_m).write_csv(USER_DIR / f"ceiling_xgb_multiclass_{suffix}.csv")
    if gp_b:
        pl.DataFrame(gp_b).write_csv(USER_DIR / f"ceiling_gpboost_binary_{suffix}.csv")
    if gp_m:
        pl.DataFrame(gp_m).write_csv(USER_DIR / f"ceiling_gpboost_ovr_{suffix}.csv")
    pl.DataFrame([{"family": k, "feature": c} for k, v in fam.items() for c in v]).write_csv(
        USER_DIR / f"ceiling_families_{suffix}.csv")

    print(f"\n✅ Resultados en {USER_DIR} (suffix: {suffix})")


if __name__ == "__main__":
    main()
