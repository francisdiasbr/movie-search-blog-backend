import pytest

from favorites import controller


@pytest.fixture
def favorites(mongo):
    collection = mongo["favoritelist"]
    collection.insert_many(
        [
            {
                "tconst": "tt0053472",
                "primaryTitle": "Breathless",
                "director": "Jean-Luc Godard",
                "country": "France",
                "startYear": "1960",
            },
            {
                "tconst": "tt0056801",
                "primaryTitle": "8½",
                "director": "Federico Fellini",
                "country": "Italy",
                "startYear": 1963,
            },
            {
                "tconst": "tt0057345",
                "primaryTitle": "Contempt",
                "director": "Jean-Luc Godard",
                "country": "France",
                "startYear": "N/A",
            },
        ]
    )
    return collection


def test_lists_favorites_newest_first_with_string_ids(favorites):
    body, status = controller.get_favorited_movies()

    assert status == 200
    assert [e["primaryTitle"] for e in body["entries"]] == [
        "Contempt",
        "8½",
        "Breathless",
    ]
    assert all(isinstance(e["_id"], str) for e in body["entries"])
    assert body["total_documents"] == 3
    assert body["current_page"] == 1
    assert body["total_pages"] == 1
    assert body["page_size"] == 10


def test_start_year_is_cast_to_int_when_possible(favorites):
    body, _ = controller.get_favorited_movies()
    years = {e["primaryTitle"]: e["startYear"] for e in body["entries"]}

    assert years == {"Breathless": 1960, "8½": 1963, "Contempt": "N/A"}


def test_facets_list_countries_and_only_numeric_years_sorted(favorites):
    favorites.insert_one({"tconst": "tt9", "startYear": None})

    body, _ = controller.get_favorited_movies()

    assert sorted(body["countries"]) == ["France", "Italy"]
    assert body["years"] == [1960, 1963]


def test_facets_ignore_the_current_search(favorites):
    body, _ = controller.get_favorited_movies(search_term="fellini")

    assert body["total_documents"] == 1
    assert sorted(body["countries"]) == ["France", "Italy"]


@pytest.mark.parametrize(
    "term, titles",
    [
        ("TT0056801", ["8½"]),
        ("breath", ["Breathless"]),
        ("godard", ["Contempt", "Breathless"]),
    ],
)
def test_search_term_matches_tconst_title_or_director_ignoring_case(
    favorites, term, titles
):
    body, status = controller.get_favorited_movies(search_term=term)

    assert status == 200
    assert [e["primaryTitle"] for e in body["entries"]] == titles


def test_filters_are_exact_matches_combined_with_the_search_term(favorites):
    body, _ = controller.get_favorited_movies(
        filters={"country": "France"}, search_term="contempt"
    )

    assert [e["tconst"] for e in body["entries"]] == ["tt0057345"]


def test_pagination_slices_and_counts_pages(favorites):
    body, status = controller.get_favorited_movies(page=2, page_size=2)

    assert status == 200
    assert [e["primaryTitle"] for e in body["entries"]] == ["Breathless"]
    assert body["total_documents"] == 3
    assert body["total_pages"] == 2
    assert body["current_page"] == 2


def test_no_sorters_keeps_insertion_order(favorites):
    body, _ = controller.get_favorited_movies(sorters=None)

    assert body["entries"][0]["primaryTitle"] == "Breathless"


def test_no_match_is_200_with_an_empty_list(favorites):
    body, status = controller.get_favorited_movies(search_term="kurosawa")

    assert status == 200
    assert body["entries"] == []
    assert body["total_documents"] == 0
    assert body["total_pages"] == 0
    # The facets still describe the whole collection.
    assert body["years"] == [1960, 1963]


def test_empty_collection_is_200_with_an_empty_list(mongo):
    body, status = controller.get_favorited_movies()

    assert status == 200
    assert body["entries"] == []
    assert body["countries"] == []


def test_page_past_the_end_is_200_with_an_empty_list(favorites):
    body, status = controller.get_favorited_movies(page=5)

    assert status == 200
    assert body["entries"] == []
    assert body["total_documents"] == 3


@pytest.mark.parametrize("paging", [{"page_size": 0}, {"page": 0}, {"page": -1}])
def test_invalid_paging_is_400(favorites, paging):
    body, status = controller.get_favorited_movies(**paging)

    assert status == 400
    assert body == {"status": 400, "message": "Paginação inválida"}


def test_database_down_is_500(database_down):
    body, status = controller.get_favorited_movies()

    assert status == 500
    assert body["error"] == "Collection not found"
