import pytest

from write_review import controller


@pytest.fixture
def reviews(mongo):
    collection = mongo[controller.COLLECTION_NAME]
    collection.insert_many(
        [
            {
                "tconst": "tt1",
                "primaryTitle": "Breathless",
                "content": {"pt": {"text": "Uma obra-prima."}},
                "isAiGenerated": False,
            },
            {
                "tconst": "tt2",
                "primaryTitle": "Contempt",
                "content": {"pt": {"text": "Belo e amargo."}},
                "isAiGenerated": True,
            },
        ]
    )
    return collection


def test_search_lists_newest_first_with_string_ids(reviews):
    body, status = controller.search_write_reviews({})

    assert status == 200
    assert body["total_documents"] == 2
    assert [r["tconst"] for r in body["entries"]] == ["tt2", "tt1"]
    assert all(isinstance(r["_id"], str) for r in body["entries"])


def test_search_title_and_tconst_are_case_insensitive_substrings(reviews):
    by_title, _ = controller.search_write_reviews({"primaryTitle": "breath"})
    by_tconst, _ = controller.search_write_reviews({"tconst": "TT2"})

    assert [r["tconst"] for r in by_title["entries"]] == ["tt1"]
    assert [r["tconst"] for r in by_tconst["entries"]] == ["tt2"]


def test_search_other_fields_match_exactly(reviews):
    body, _ = controller.search_write_reviews({"isAiGenerated": True})

    assert [r["tconst"] for r in body["entries"]] == ["tt2"]


def test_search_content_filter_looks_inside_the_texts_of_each_language(reviews):
    reviews.insert_one(
        {"tconst": "tt3", "content": {"en": {"text": "A bitter masterpiece."}}}
    )
    reviews.insert_one({"tconst": "tt4", "content": "Texto antigo, amargo."})

    portuguese, status = controller.search_write_reviews({"content": "OBRA-PRIMA"})
    english, _ = controller.search_write_reviews({"content": "masterpiece"})
    both, _ = controller.search_write_reviews({"content": "amarg|bitter"})
    none, _ = controller.search_write_reviews({"content": "western"})

    assert status == 200
    assert [r["tconst"] for r in portuguese["entries"]] == ["tt1"]
    assert [r["tconst"] for r in english["entries"]] == ["tt3"]
    assert [r["tconst"] for r in both["entries"]] == ["tt4", "tt3", "tt2"]
    assert none == {"total_documents": 0, "entries": []}


def test_search_content_filter_combines_with_the_other_filters(reviews):
    body, _ = controller.search_write_reviews({"content": "a", "isAiGenerated": True})

    assert [r["tconst"] for r in body["entries"]] == ["tt2"]


def test_search_with_null_filters_means_no_filter(reviews):
    body, status = controller.search_write_reviews(None)

    assert status == 200
    assert body["total_documents"] == 2


def test_search_paginates(reviews):
    body, _ = controller.search_write_reviews({}, page=2, page_size=1)

    assert body["total_documents"] == 2
    assert [r["tconst"] for r in body["entries"]] == ["tt1"]


def test_search_with_the_database_down_is_500(database_down):
    body, status = controller.search_write_reviews({})

    assert status == 500
    assert body["status"] == 500


def test_get_returns_the_review_of_the_movie(reviews):
    body, status = controller.get_write_review("tt1")

    assert status == 200
    assert body["data"]["content"] == {"pt": {"text": "Uma obra-prima."}}
    assert isinstance(body["data"]["_id"], str)


def test_get_unknown_movie_is_404(reviews):
    body, status = controller.get_write_review("tt9")

    assert status == 404
    assert body == {"status": 404, "message": "Opinião não encontrada"}


def test_get_with_the_database_down_is_500(database_down):
    assert controller.get_write_review("tt1")[1] == 500


def test_get_all_returns_every_review(reviews):
    body, status = controller.get_all_write_reviews()

    assert status == 200
    assert sorted(r["tconst"] for r in body["data"]) == ["tt1", "tt2"]
    assert all(isinstance(r["_id"], str) for r in body["data"])


def test_get_all_with_the_database_down_is_500(database_down):
    assert controller.get_all_write_reviews()[1] == 500
