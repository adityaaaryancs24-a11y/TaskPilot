from __future__ import annotations


from core.embedding_model import get_embedding, cosine_similarity


class TestEmbeddingModel:
    def test_get_embedding_returns_list(self):
        emb = get_embedding("test text")
        assert isinstance(emb, list)
        assert len(emb) > 0

    def test_similar_texts_have_high_similarity(self):
        emb1 = get_embedding("Fix the login page bug")
        emb2 = get_embedding("Fix the login bug on the page")
        score = cosine_similarity(emb1, emb2)
        assert score > 0.5

    def test_different_texts_have_low_similarity(self):
        emb1 = get_embedding("Fix the login page bug")
        emb2 = get_embedding("Order pizza for lunch")
        score = cosine_similarity(emb1, emb2)
        assert score < 0.5

    def test_cosine_similarity_same_vector(self):
        emb = get_embedding("test")
        score = cosine_similarity(emb, emb)
        assert abs(score - 1.0) < 0.001

    def test_cosine_similarity_zero_vector(self):
        score = cosine_similarity([0.0, 0.0], [0.5, 0.5])
        assert score == 0.0
