import pytest

import movie_prepopulate.controller
from recommendations import controller


@pytest.fixture
def recommendations(mongo):
    collection = mongo["recommendations"]
    collection.insert_many(
        [
            {
                "tconst": "tt2",
                "title": "Contempt",
                "director": "Jean-Luc Godard",
                "position": 2,
            },
            {
                "tconst": "tt1",
                "title": "Breathless",
                "director": "Jean-Luc Godard",
                "position": 1,
            },
            {
                "tconst": "tt3",
                "title": "Cléo from 5 to 7",
                "director": "Agnès Varda",
                "position": 3,
            },
        ]
    )
    return collection


@pytest.fixture
def prepopulate(monkeypatch):
    """Replaces the prepopulation step, recording the movies it receives."""
    calls = []

    def prepopulate_movie_data(movie, language):
        calls.append((movie["tconst"], language))
        return {"status": "success", "results": {}}

    monkeypatch.setattr(
        movie_prepopulate.controller, "prepopulate_movie_data", prepopulate_movie_data
    )
    return calls


@pytest.fixture
def broken_prepopulate(monkeypatch):
    def prepopulate_movie_data(movie, language):
        raise RuntimeError("prepopulate exploded")

    monkeypatch.setattr(
        movie_prepopulate.controller, "prepopulate_movie_data", prepopulate_movie_data
    )


def test_random_returns_everything_ordered_by_position(recommendations):
    """The route name is historical: the frontend shows the watchlist in order."""
    body, status = controller.get_random_recommendations()

    assert status == 200
    assert body["total"] == 3
    assert [r["tconst"] for r in body["data"]] == ["tt1", "tt2", "tt3"]
    assert all(isinstance(r["_id"], str) for r in body["data"])


def test_random_on_an_empty_collection_is_200(mongo):
    assert controller.get_random_recommendations() == ({"data": [], "total": 0}, 200)


def test_random_with_the_database_down_is_500(database_down):
    body, status = controller.get_random_recommendations()

    assert status == 500
    assert body == {"status": 500, "message": "Erro ao buscar recomendações"}


def test_all_paginates_by_position(recommendations):
    body, status = controller.get_all_recommendations(page=2, page_size=2)

    assert status == 200
    assert body["total_documents"] == 3
    assert [r["tconst"] for r in body["entries"]] == ["tt3"]
    assert isinstance(body["entries"][0]["_id"], str)


@pytest.mark.parametrize(
    "term, expected",
    [
        ("tt2", ["tt2"]),
        ("TT2", []),
        ("tt", []),
        ("breath", ["tt1"]),
        ("GODARD", ["tt1", "tt2"]),
        ("kurosawa", []),
    ],
)
def test_search_is_exact_on_tconst_and_fuzzy_on_title_and_director(
    recommendations, term, expected
):
    body, status = controller.get_all_recommendations(search_term=term)

    assert status == 200
    assert [r["tconst"] for r in body["entries"]] == expected
    assert body["total_documents"] == len(expected)


def test_all_with_the_database_down_is_500(database_down):
    assert controller.get_all_recommendations()[1] == 500


def test_delete_removes_one_recommendation(recommendations):
    body, status = controller.delete_recommendation("tt2")

    assert status == 200
    assert body == {"data": "Recommendation tt2 deleted"}
    assert recommendations.count_documents({}) == 2


def test_delete_unknown_recommendation_is_404(recommendations):
    body, status = controller.delete_recommendation("tt9")

    assert status == 404
    assert body == {"data": "Recommendation tt9 not found"}
    assert recommendations.count_documents({}) == 3


def test_delete_with_the_database_down_is_500(database_down):
    assert controller.delete_recommendation("tt1")[1] == 500


def test_clear_removes_everything_and_reports_the_count(recommendations):
    body, status = controller.clear_all_recommendations()

    assert status == 200
    assert body == {"data": "3 recommendations deleted"}
    assert recommendations.count_documents({}) == 0


def test_clear_with_the_database_down_is_500(database_down):
    assert controller.clear_all_recommendations()[1] == 500


def test_add_appends_the_movie_at_the_end_of_the_list(recommendations):
    body, status = controller.add_recommendation(
        {"tconst": "tt4", "title": "Vagabond"}, prepopulate=False
    )

    assert status == 201
    assert body["data"] == "Filme adicionado com sucesso"
    assert body["movie"]["position"] == 4
    assert isinstance(body["movie"]["_id"], str)
    assert "prepopulate" not in body
    assert recommendations.find_one({"tconst": "tt4"})["position"] == 4


def test_first_movie_gets_position_one(mongo):
    body, _ = controller.add_recommendation({"tconst": "tt1"}, prepopulate=False)

    assert body["movie"]["position"] == 1


def test_add_keeps_an_explicit_position(recommendations):
    body, _ = controller.add_recommendation(
        {"tconst": "tt4", "position": 1}, prepopulate=False
    )

    assert body["movie"]["position"] == 1


def test_add_refuses_a_duplicate_tconst(recommendations):
    body, status = controller.add_recommendation({"tconst": "tt1"}, prepopulate=False)

    assert status == 400
    assert body == {"error": "Filme já existe na base de dados"}
    assert recommendations.count_documents({}) == 3


@pytest.mark.parametrize(
    "movie", [{"title": "A"}, {"tconst": ""}, {"tconst": "  "}, {"tconst": None}]
)
def test_add_requires_a_tconst(recommendations, prepopulate, movie):
    body, status = controller.add_recommendation(movie)

    assert status == 400
    assert body == {"error": "tconst é obrigatório"}
    assert recommendations.count_documents({}) == 3
    assert prepopulate == []


def test_add_prepopulates_the_new_movie_by_default(recommendations, prepopulate):
    body, status = controller.add_recommendation({"tconst": "tt4"}, "en")

    assert status == 201
    assert body["data"] == "Filme adicionado e dados pré-populados com sucesso"
    assert body["prepopulate"] == {"status": "success", "results": {}}
    assert prepopulate == [("tt4", "en")]


def test_duplicate_is_not_prepopulated(recommendations, prepopulate):
    controller.add_recommendation({"tconst": "tt1"})

    assert prepopulate == []


def test_add_survives_a_prepopulation_crash(recommendations, broken_prepopulate):
    body, status = controller.add_recommendation({"tconst": "tt4"})

    assert status == 201
    assert body["data"] == "Filme adicionado com sucesso (pré-população falhou)"
    assert body["prepopulate_error"] == "prepopulate exploded"
    assert recommendations.count_documents({"tconst": "tt4"}) == 1


def test_add_with_the_database_down_is_500(database_down):
    body, status = controller.add_recommendation({"tconst": "tt4"})

    assert status == 500
    assert body["error"].startswith("Erro ao adicionar filme:")


@pytest.mark.parametrize("payload", [["tt4"], "tt4", 4, None])
def test_add_with_a_non_object_payload_is_400(recommendations, payload):
    body, status = controller.add_recommendation(payload)

    assert status == 400
    assert body == {"error": "Dados do filme inválidos"}
    assert recommendations.count_documents({}) == 3


def test_add_ignores_documents_without_position_when_numbering(mongo):
    mongo["recommendations"].insert_many(
        [{"tconst": "tt1"}, {"tconst": "tt2", "position": 4}, {"tconst": "tt3"}]
    )

    body, status = controller.add_recommendation({"tconst": "tt4"}, prepopulate=False)

    assert status == 201
    assert body["movie"]["position"] == 5


def test_bulk_add_inserts_only_the_new_movies_in_sequence(recommendations):
    movies = [
        {"tconst": "tt1", "title": "Breathless"},
        {"tconst": "tt4", "title": "Vagabond"},
        {"tconst": "tt5", "title": "Pierrot le Fou", "position": 50},
        {"tconst": "tt6", "title": "Le Bonheur"},
    ]

    body, status = controller.bulk_add_recommendations(movies, prepopulate=False)

    assert status == 201
    assert body["data"] == "3 filmes adicionados com sucesso"
    assert body["skipped"] == 1
    assert body["prepopulate_results"] == []
    assert [(m["tconst"], m["position"]) for m in body["movies"]] == [
        ("tt4", 4),
        ("tt5", 50),
        ("tt6", 5),
    ]
    assert all(isinstance(m["_id"], str) for m in body["movies"])
    assert recommendations.count_documents({}) == 6


def test_bulk_add_into_an_empty_collection_starts_at_one(mongo):
    body, _ = controller.bulk_add_recommendations(
        [{"tconst": "tt1"}, {"tconst": "tt2"}], prepopulate=False
    )

    assert [m["position"] for m in body["movies"]] == [1, 2]


def test_bulk_add_with_only_known_movies_is_400(recommendations):
    body, status = controller.bulk_add_recommendations(
        [{"tconst": "tt1"}, {"tconst": "tt2"}], prepopulate=False
    )

    assert status == 400
    assert body == {"error": "Todos os filmes já existem na base de dados"}
    assert recommendations.count_documents({}) == 3


def test_bulk_add_inserts_a_repeated_tconst_only_once(recommendations, prepopulate):
    movies = [
        {"tconst": "tt4", "title": "First"},
        {"tconst": "tt4", "title": "Repeated"},
        {"tconst": "tt5"},
    ]

    body, status = controller.bulk_add_recommendations(movies)

    assert status == 201
    assert body["data"] == "2 filmes adicionados com sucesso"
    assert body["skipped"] == 1
    assert [(m["tconst"], m["position"]) for m in body["movies"]] == [
        ("tt4", 4),
        ("tt5", 5),
    ]
    assert recommendations.find_one({"tconst": "tt4"})["title"] == "First"
    assert recommendations.count_documents({"tconst": "tt4"}) == 1
    assert prepopulate == [("tt4", "pt"), ("tt5", "pt")]


def test_bulk_add_skips_entries_without_tconst(recommendations):
    movies = [{"title": "No id"}, "tt7", {"tconst": ""}, {"tconst": "tt4"}]

    body, status = controller.bulk_add_recommendations(movies, prepopulate=False)

    assert status == 201
    assert [m["tconst"] for m in body["movies"]] == ["tt4"]
    assert body["skipped"] == 3
    assert recommendations.count_documents({}) == 4


def test_bulk_add_with_nothing_valid_is_400(recommendations):
    body, status = controller.bulk_add_recommendations(
        [{"title": "No id"}], prepopulate=False
    )

    assert status == 400
    assert recommendations.count_documents({}) == 3


def test_bulk_add_prepopulates_each_new_movie(recommendations, prepopulate):
    movies = [{"tconst": "tt1"}, {"tconst": "tt4", "title": "Vagabond"}]

    body, status = controller.bulk_add_recommendations(movies, "en")

    assert status == 201
    assert prepopulate == [("tt4", "en")]
    assert body["prepopulate_results"] == [
        {
            "tconst": "tt4",
            "title": "Vagabond",
            "result": {"status": "success", "results": {}},
        }
    ]


def test_bulk_add_survives_a_prepopulation_crash(recommendations, broken_prepopulate):
    body, status = controller.bulk_add_recommendations([{"tconst": "tt4"}])

    assert status == 201
    assert body["prepopulate_results"] == [{"error": "prepopulate exploded"}]
    assert recommendations.count_documents({"tconst": "tt4"}) == 1


def test_bulk_add_ignores_documents_without_position_when_numbering(mongo):
    mongo["recommendations"].insert_one({"tconst": "tt1"})

    body, status = controller.bulk_add_recommendations(
        [{"tconst": "tt2"}, {"tconst": "tt3"}], prepopulate=False
    )

    assert status == 201
    assert [m["position"] for m in body["movies"]] == [1, 2]


def test_bulk_add_with_the_database_down_is_500(database_down):
    body, status = controller.bulk_add_recommendations([{"tconst": "tt4"}])

    assert status == 500
    assert body["error"].startswith("Erro ao adicionar filmes:")
