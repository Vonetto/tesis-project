"""Tests del sequence_embedding_pack - Etapa B (bigramas y matriz de conteo).

Correr:
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python -m pytest \
    lib/test_user_sequence_embedding.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "audits"))
from build_user_sequence_embedding_features import (  # noqa: E402
    BIGRAM_SEP,
    build_bigrams_lf,
    build_count_matrix,
    compute_vocab,
)


def make_seqs() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "id_tarjeta": ["three", "two", "one", "zero"],
            "seq_tokens": [
                ["A", "B", "C"],  # bigrams: A>>B, B>>C
                ["A", "B"],  # bigrams: A>>B
                ["A"],  # sin bigramas (seq_n_tokens < 2)
                [],  # sin tokens
            ],
            "seq_n_tokens": [3, 2, 1, 0],
        }
    )


def test_bigram_pairing_is_lockstep() -> None:
    """explode(['seq_a','seq_b']) debe parear elementos por indice, no producir
    un producto cruzado. Para "three" (A,B,C) los bigramas deben ser
    A>>B y B>>C, NUNCA A>>C, B>>B, etc."""
    bigrams = build_bigrams_lf(make_seqs()).collect()

    three = bigrams.filter(pl.col("id_tarjeta") == "three")["bigram"].to_list()
    assert sorted(three) == sorted([f"A{BIGRAM_SEP}B", f"B{BIGRAM_SEP}C"])
    assert len(three) == 2  # no cross product (que daria 2*2=4 o mas)


def test_two_token_sequence_one_bigram() -> None:
    bigrams = build_bigrams_lf(make_seqs()).collect()
    two = bigrams.filter(pl.col("id_tarjeta") == "two")["bigram"].to_list()
    assert two == [f"A{BIGRAM_SEP}B"]


def test_short_sequences_excluded() -> None:
    """Tarjetas con seq_n_tokens < 2 no aportan bigramas ni filas."""
    bigrams = build_bigrams_lf(make_seqs()).collect()
    ids_with_bigrams = set(bigrams["id_tarjeta"].to_list())
    assert "one" not in ids_with_bigrams
    assert "zero" not in ids_with_bigrams


def test_compute_vocab_orders_by_frequency() -> None:
    seqs = pl.DataFrame(
        {
            "id_tarjeta": ["c1", "c2", "c3"],
            "seq_tokens": [
                ["A", "B", "A", "B"],  # bigrams: A>>B, B>>A, A>>B -> A>>B x2, B>>A x1
                ["A", "B"],  # A>>B
                ["X", "Y"],  # X>>Y
            ],
            "seq_n_tokens": [4, 2, 2],
        }
    )
    bigrams_lf = build_bigrams_lf(seqs)
    vocab, vocab_counts = compute_vocab(bigrams_lf)
    # A>>B aparece 3 veces en total (2 en c1, 1 en c2), debe ser el mas frecuente.
    assert vocab[0] == f"A{BIGRAM_SEP}B"
    assert vocab_counts.filter(pl.col("bigram") == f"A{BIGRAM_SEP}B")["len"].item() == 3


def test_build_count_matrix_shape_and_values() -> None:
    seqs = make_seqs()
    bigrams_lf = build_bigrams_lf(seqs)
    vocab = [f"A{BIGRAM_SEP}B", f"B{BIGRAM_SEP}C", f"X{BIGRAM_SEP}Y"]  # X>>Y no aparece en los datos
    ids = seqs["id_tarjeta"]

    mat = build_count_matrix(bigrams_lf, vocab, ids)

    assert mat.shape == (4, 3)

    dense = mat.toarray()
    id_to_row = {c: i for i, c in enumerate(ids.to_list())}

    # "three": A>>B=1, B>>C=1, X>>Y=0
    assert dense[id_to_row["three"], 0] == 1
    assert dense[id_to_row["three"], 1] == 1
    assert dense[id_to_row["three"], 2] == 0

    # "two": A>>B=1, resto 0
    assert dense[id_to_row["two"], 0] == 1
    assert dense[id_to_row["two"], 1] == 0

    # "one" y "zero": filas todas en cero (sin bigramas)
    assert dense[id_to_row["one"]].sum() == 0
    assert dense[id_to_row["zero"]].sum() == 0


def test_count_matrix_row_order_matches_ids() -> None:
    """La fila i de la matriz corresponde a ids[i], incluso si bigrams_lf
    no preserva el orden original de id_tarjeta."""
    seqs = make_seqs()
    bigrams_lf = build_bigrams_lf(seqs)
    vocab, _ = compute_vocab(bigrams_lf)
    ids = seqs["id_tarjeta"]

    mat = build_count_matrix(bigrams_lf, vocab, ids)
    dense = mat.toarray()

    # Para cada tarjeta con bigramas, el total de conteos en su fila debe
    # igualar el numero de bigramas que efectivamente caen en el vocabulario.
    bigrams = bigrams_lf.collect()
    for i, card in enumerate(ids.to_list()):
        n_bigrams_in_vocab = bigrams.filter(
            (pl.col("id_tarjeta") == card) & (pl.col("bigram").is_in(vocab))
        ).height
        assert dense[i].sum() == n_bigrams_in_vocab
