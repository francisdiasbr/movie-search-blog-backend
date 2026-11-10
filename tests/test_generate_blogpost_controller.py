import pytest

from generate_blogpost import controller


@pytest.fixture
def posts(mongo):
    collection = mongo["blogposts"]
    collection.insert_many(
        [
            {
                "tconst": "tt1",
                "primaryTitle": "Breathless",
                "introduction": "A jump cut manifesto.",
                "isAiGenerated": True,
            },
            {
                "tconst": "tt2",
                "primaryTitle": "Contempt",
                "introduction": "Cinema about cinema.",
                "isAiGenerated": False,
            },
            {
                "tconst": "tt3",
                "primaryTitle": "Breathless (1983)",
                "introduction": "The remake.",
                "isAiGenerated": False,
            },
        ]
    )
    return collection


def test_search_without_filters_lists_newest_first(posts):
    body, status = controller.search_blog_post({})

    assert status == 200
    assert body["total_documents"] == 3
    assert [p["tconst"] for p in body["entries"]] == ["tt3", "tt2", "tt1"]
    assert all(isinstance(p["_id"], str) for p in body["entries"])


def test_text_fields_match_as_case_insensitive_substrings(posts):
    body, status = controller.search_blog_post({"filters": {"primaryTitle": "BREATH"}})

    assert status == 200
    assert [p["tconst"] for p in body["entries"]] == ["tt3", "tt1"]


def test_other_fields_match_exactly(posts):
    body, _ = controller.search_blog_post(
        {"filters": {"isAiGenerated": False, "introduction": "cinema"}}
    )

    assert [p["tconst"] for p in body["entries"]] == ["tt2"]


def test_search_paginates(posts):
    body, status = controller.search_blog_post({"page": 2, "page_size": 2})

    assert status == 200
    assert body["total_documents"] == 3
    assert [p["tconst"] for p in body["entries"]] == ["tt1"]


def test_search_without_matches_is_404_with_an_empty_list(posts):
    body, status = controller.search_blog_post({"filters": {"tconst": "tt9"}})

    assert status == 404
    assert body == {"total_documents": 0, "entries": []}


def test_page_past_the_end_is_200_with_no_entries(posts):
    """Unlike favorites, the status follows the total, not the page."""
    body, status = controller.search_blog_post({"page": 9})

    assert status == 200
    assert body == {"total_documents": 3, "entries": []}


def test_search_with_the_database_down_is_500(database_down):
    body, status = controller.search_blog_post({})

    assert status == 500
    assert body["status"] == 500


def test_get_blog_post_returns_the_post(posts):
    body, status = controller.get_blog_post("tt2")

    assert status == 200
    assert body["data"]["primaryTitle"] == "Contempt"
    assert isinstance(body["data"]["_id"], str)


def test_get_blog_post_unknown_is_404(posts):
    body, status = controller.get_blog_post("tt9")

    assert status == 404
    assert body == {"status": "erro", "mensagem": "Post não encontrado"}


def test_get_blog_post_with_the_database_down_is_500(database_down):
    body, status = controller.get_blog_post("tt1")

    assert status == 500
    assert body["status"] == "erro"
