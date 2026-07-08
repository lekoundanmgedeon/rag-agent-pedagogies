import numpy as np

from agent_tuteur.vectorstore.embeddings import LightEmbedder


def test_dense_is_l2_normalized_and_right_dim():
    emb = LightEmbedder(dim=128)
    v = emb.embed_query("dérivée d'un quotient")
    assert v.dense.shape == (128,)
    assert np.isclose(np.linalg.norm(v.dense), 1.0, atol=1e-5)


def test_deterministic_across_instances():
    a = LightEmbedder(dim=64).embed_query("masse et poids")
    b = LightEmbedder(dim=64).embed_query("masse et poids")
    assert np.allclose(a.dense, b.dense)
    assert a.sparse == b.sparse


def test_sparse_weights_are_log1p_tf():
    emb = LightEmbedder(dim=64)
    v = emb.embed_query("mot mot mot autre")  # « mot » x3, « autre » x1
    weights = sorted(v.sparse.values())
    # log1p(1) ≈ 0.693 pour « autre », log1p(3) ≈ 1.386 pour « mot ».
    assert np.isclose(weights[0], np.log1p(1), atol=1e-6)
    assert np.isclose(weights[-1], np.log1p(3), atol=1e-6)


def test_accent_insensitive_tokens():
    emb = LightEmbedder(dim=64)
    assert emb.embed_query("dérivée").sparse == emb.embed_query("derivee").sparse
