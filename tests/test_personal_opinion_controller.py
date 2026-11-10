import pytest

from personal_opinion import controller


@pytest.fixture
def opinions(mongo):
    collection = mongo[controller.COLLECTION_NAME]
    collection.insert_many(
        [
            {
                "tconst": "tt1",
                "opinion": "A masterpiece of the Nouvelle Vague.",
                "enjoying_1": "Jump cuts",
                "enjoying_2": "Jean Seberg",
                "rating": 5,
            },
            {
                "tconst": "tt2",
                "opinion": "Beautiful and bitter.",
                "enjoying_1": "Capri",
                "enjoying_2": "Georges Delerue",
                "rating": 4,
            },
        ]
    )
    return collection


def test_search_lists_newest_first_with_string_ids(opinions):
    body, status = controller.search_personal_opinions({})

    assert status == 200
    assert body["total_documents"] == 2
    assert [o["tconst"] for o in body["entries"]] == ["tt2", "tt1"]
    assert all(isinstance(o["_id"], str) for o in body["entries"])


def test_search_text_fields_are_case_insensitive_substrings(opinions):
    body, _ = controller.search_personal_opinions({"opinion": "MASTERPIECE"})

    assert [o["tconst"] for o in body["entries"]] == ["tt1"]


def test_search_other_fields_match_exactly(opinions):
    body, _ = controller.search_personal_opinions({"rating": 4})

    assert [o["tconst"] for o in body["entries"]] == ["tt2"]


def test_search_paginates(opinions):
    body, status = controller.search_personal_opinions({}, page=2, page_size=1)

    assert status == 200
    assert body["total_documents"] == 2
    assert [o["tconst"] for o in body["entries"]] == ["tt1"]


def test_search_without_matches_is_still_200(opinions):
    body, status = controller.search_personal_opinions({"tconst": "tt9"})

    assert status == 200
    assert body == {"total_documents": 0, "entries": []}


def test_search_with_null_filters_is_500(opinions):
    """Current behaviour: `filters` is iterated without a None check."""
    assert controller.search_personal_opinions(None)[1] == 500


def test_search_with_the_database_down_is_500(database_down):
    body, status = controller.search_personal_opinions({})

    assert status == 500
    assert body["message"] == "Erro ao pesquisar opiniões pessoais"


def test_get_returns_the_opinion_of_the_movie(opinions):
    body, status = controller.get_personal_opinion("tt2")

    assert status == 200
    assert body["data"]["enjoying_1"] == "Capri"
    assert isinstance(body["data"]["_id"], str)


def test_get_unknown_movie_is_404(opinions):
    body, status = controller.get_personal_opinion("tt9")

    assert status == 404
    assert body == {"status": 404, "message": "Opinião não encontrada"}


def test_get_with_the_database_down_is_500(database_down):
    assert controller.get_personal_opinion("tt1")[1] == 500


def test_get_all_returns_every_opinion(opinions):
    body, status = controller.get_all_personal_opinions()

    assert status == 200
    assert sorted(o["tconst"] for o in body["data"]) == ["tt1", "tt2"]
    assert all(isinstance(o["_id"], str) for o in body["data"])


def test_get_all_on_an_empty_collection_is_200(mongo):
    assert controller.get_all_personal_opinions() == ({"data": []}, 200)


def test_get_all_with_the_database_down_is_500(database_down):
    assert controller.get_all_personal_opinions()[1] == 500


def test_update_writes_only_the_allowed_fields(opinions):
    body, status = controller.update_personal_opinion(
        "tt1", {"opinion": "Even better now.", "tconst": "tt666", "rating": 1}
    )
    stored = opinions.find_one({"tconst": "tt1"})

    assert status == 200
    assert body == {"status": 200, "message": "Opinião atualizada com sucesso"}
    assert stored["opinion"] == "Even better now."
    assert stored["rating"] == 5
    assert stored["enjoying_1"] == "Jump cuts"
    assert opinions.count_documents({"tconst": "tt666"}) == 0


def test_update_unknown_movie_is_404(opinions):
    body, status = controller.update_personal_opinion("tt9", {"opinion": "x"})

    assert status == 404
    assert opinions.count_documents({}) == 2


def test_update_with_the_same_values_is_400(opinions):
    """Current behaviour: an idempotent edit is reported as a client error."""
    body, status = controller.update_personal_opinion("tt2", {"enjoying_1": "Capri"})

    assert status == 400
    assert body == {"status": 400, "message": "Nenhuma alteração realizada"}


def test_update_with_the_database_down_is_500(database_down):
    assert controller.update_personal_opinion("tt1", {"opinion": "x"})[1] == 500
