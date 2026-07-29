"""Etapa B (sequence_embedding_pack, 2026-06-13): NMF sobre bigramas de tokens.

Contexto: Etapa A (build_user_sequence_tokens.py) construyo, por id_tarjeta,
la secuencia de tokens de viaje ordenada en el tiempo
(seq_tokens = lista de "macro_origen__macro_destino__banda__modo").

Esta etapa B:
  1. Construye bigramas consecutivos de esa secuencia: (seq_tokens[i], seq_tokens[i+1]).
  2. Cuenta, por id_tarjeta, cuantas veces aparece cada uno de los TOP_K_BIGRAMS
     bigramas mas frecuentes globalmente (vocabulario fijo, decidido una vez
     sobre todo el scope).
  3. Arma una matriz sparse (n_cards x TOP_K_BIGRAMS) de conteos.
  4. Corre NMF (sklearn, solver="cd", beta_loss="frobenius") para una grilla
     de k en NMF_KS, ajustando sobre una muestra (FIT_SAMPLE_SIZE tarjetas)
     y transformando la matriz completa para obtener los scores por tarjeta.

Output: un parquet por k, con columnas id_tarjeta + nmf_seq_k{k}_c0..c{k-1}.
La Etapa C decide, via benchmark binario, que k (o si ninguno) aporta senal.

Decisiones de diseno (confirmadas con el usuario, 2026-06-13):
  - Solo bigramas (no trigramas): secuencias son cortas (mediana 7 tokens),
    trigramas diluirian demasiado los conteos.
  - Vocabulario = top 300 bigramas mas frecuentes (TOP_K_BIGRAMS).
  - Grilla de k = 10, 15, 20 (NMF_KS); Etapa C compara por AUC, no por
    reconstruction error / elbow.

Uso:
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
    scripts/audits/build_user_sequence_embedding_features.py --scope interannual_ml --force
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import polars as pl
from scipy import sparse
from sklearn.decomposition import NMF
from threadpoolctl import threadpool_limits

from build_user_routine_features import OUT_DIR, SCOPE_WEEKS, validate_inputs
from build_user_sequence_tokens import output_path as sequence_tokens_path

TOP_K_BIGRAMS = 300
NMF_KS = [10, 15, 20]
FIT_SAMPLE_SIZE = 200_000
MAX_ITER = 200
TOL = 1e-4
SEED = 20260613
BLAS_THREADS = 4
BIGRAM_SEP = ">>"


def output_path(scope: str, k: int) -> Path:
    return OUT_DIR / f"user_sequence_embedding_features_k{k}_{scope}.parquet"


def vocab_path(scope: str) -> Path:
    return OUT_DIR / f"user_sequence_embedding_vocab_{scope}.csv"


def audit_path(scope: str) -> Path:
    return OUT_DIR / f"user_sequence_embedding_summary_{scope}.csv"


def load_sequences(scope: str) -> pl.DataFrame:
    path = sequence_tokens_path(scope)
    if not path.exists():
        raise FileNotFoundError(f"Falta {path}. Correr build_user_sequence_tokens.py primero.")
    return pl.read_parquet(path).select("id_tarjeta", "seq_tokens", "seq_n_tokens")


def build_bigrams_lf(seqs: pl.DataFrame) -> pl.LazyFrame:
    """Por id_tarjeta: lista de bigramas "tok_i>>tok_{i+1}" para tarjetas con >=2 tokens.

    No existe un operador directo en el namespace `list` de polars para
    concatenar elemento-a-elemento dos listas paralelas, asi que se explota
    cada lista (seq_a = tokens[0:n-1], seq_b = tokens[1:n]) y se concatena
    par a par con concat_str sobre las columnas explotadas.

    El largo usado para los slices se recalcula desde `seq_tokens.list.len()`
    en vez de confiar en la columna `seq_n_tokens` del parquet de Etapa A:
    un bug (corregido 2026-06-13) dejaba `seq_n_tokens` desincronizado del
    largo real para tarjetas truncadas a MAX_SEQ_LEN, lo que rompia el
    explode con un ShapeError.
    """
    lf = (
        seqs.lazy()
        .with_columns(pl.col("seq_tokens").list.len().alias("_n"))
        .filter(pl.col("_n") >= 2)
        .with_columns(
            pl.col("seq_tokens").list.slice(0, pl.col("_n") - 1).alias("seq_a"),
            pl.col("seq_tokens").list.slice(1, pl.col("_n") - 1).alias("seq_b"),
        )
        .select("id_tarjeta", "seq_a", "seq_b")
        .explode(["seq_a", "seq_b"])
        .with_columns((pl.col("seq_a") + BIGRAM_SEP + pl.col("seq_b")).alias("bigram"))
        .select("id_tarjeta", "bigram")
    )
    return lf


def compute_vocab(bigrams_lf: pl.LazyFrame) -> list[str]:
    top = (
        bigrams_lf.group_by("bigram")
        .len()
        .sort("len", descending=True)
        .head(TOP_K_BIGRAMS)
        .collect()
    )
    return top["bigram"].to_list(), top


def build_count_matrix(
    bigrams_lf: pl.LazyFrame, vocab: list[str], ids: pl.Series
) -> sparse.csr_matrix:
    """Matriz sparse (n_cards x len(vocab)) de conteos de bigramas, en el orden de `ids`."""
    vocab_index = {b: j for j, b in enumerate(vocab)}
    id_index = {c: i for i, c in enumerate(ids.to_list())}

    counts = (
        bigrams_lf.filter(pl.col("bigram").is_in(vocab))
        .group_by(["id_tarjeta", "bigram"])
        .len()
        .collect()
    )

    rows = np.fromiter((id_index[t] for t in counts["id_tarjeta"].to_list()), dtype=np.int64, count=counts.height)
    cols = np.fromiter((vocab_index[b] for b in counts["bigram"].to_list()), dtype=np.int64, count=counts.height)
    data = counts["len"].to_numpy().astype(np.float64)

    mat = sparse.coo_matrix((data, (rows, cols)), shape=(len(ids), len(vocab)))
    return mat.tocsr()


def sample_indices(n: int, sample_size: int, seed: int) -> np.ndarray:
    if sample_size >= n:
        return np.arange(n)
    rng = np.random.default_rng(seed)
    return rng.choice(n, size=sample_size, replace=False)


def fit_transform_nmf(X: sparse.csr_matrix, k: int) -> np.ndarray:
    idx = sample_indices(X.shape[0], FIT_SAMPLE_SIZE, SEED + k)
    X_sample = X[idx]
    with threadpool_limits(limits=BLAS_THREADS):
        model = NMF(
            n_components=k,
            init="random",
            random_state=SEED + k,
            max_iter=MAX_ITER,
            tol=TOL,
            solver="cd",
            beta_loss="frobenius",
        )
        model.fit(X_sample)
        w_full = model.transform(X)
    return w_full, model.reconstruction_err_


def build_sequence_embedding(scope: str, *, force: bool) -> None:
    weeks = SCOPE_WEEKS[scope]
    validate_inputs(scope, weeks)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    out_paths = [output_path(scope, k) for k in NMF_KS]
    if all(p.exists() for p in out_paths) and not force:
        print("OK exists (todos los k):")
        for p in out_paths:
            print(f"  {p}")
        return

    print(f"Cargando secuencias scope={scope}")
    seqs = load_sequences(scope)
    bigrams_lf = build_bigrams_lf(seqs)

    print(f"Calculando vocabulario top-{TOP_K_BIGRAMS} bigramas")
    vocab, vocab_counts = compute_vocab(bigrams_lf)
    vocab_counts.write_csv(vocab_path(scope))

    ids = seqs["id_tarjeta"]
    print(f"Construyendo matriz sparse {len(ids):,} x {len(vocab)}")
    X = build_count_matrix(bigrams_lf, vocab, ids)
    n_nonzero = X.nnz
    n_cards_with_bigram = int((np.asarray(X.sum(axis=1)).ravel() > 0).sum())

    summary_rows = [
        {"metric": "scope", "value": scope},
        {"metric": "n_cards", "value": str(len(ids))},
        {"metric": "n_cards_with_bigram", "value": str(n_cards_with_bigram)},
        {"metric": "top_k_bigrams", "value": str(TOP_K_BIGRAMS)},
        {"metric": "matrix_nnz", "value": str(n_nonzero)},
        {"metric": "matrix_density", "value": f"{n_nonzero / (X.shape[0] * X.shape[1]):.8f}"},
    ]

    for k in NMF_KS:
        print(f"NMF k={k} (fit_sample={min(FIT_SAMPLE_SIZE, X.shape[0]):,})")
        t0 = time.perf_counter()
        w_full, recon_err = fit_transform_nmf(X, k)
        dt = time.perf_counter() - t0
        print(f"  reconstruction_error={recon_err:.4f} fit+transform={dt:.1f}s")

        score_cols = {f"nmf_seq_k{k}_c{j}": w_full[:, j].astype(np.float32) for j in range(k)}
        out = pl.DataFrame({"id_tarjeta": ids, **score_cols})
        out.write_parquet(output_path(scope, k), compression="zstd")
        summary_rows.append({"metric": f"k{k}_reconstruction_error", "value": f"{recon_err:.6f}"})
        summary_rows.append({"metric": f"k{k}_fit_transform_seconds", "value": f"{dt:.1f}"})

    pl.DataFrame(summary_rows).write_csv(audit_path(scope))
    print("OK:")
    for p in out_paths:
        print(f"  {p}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build sequence_embedding (NMF sobre bigramas) features.")
    parser.add_argument("--scope", choices=sorted(SCOPE_WEEKS), default="interannual_ml")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_sequence_embedding(args.scope, force=args.force)


if __name__ == "__main__":
    main()
