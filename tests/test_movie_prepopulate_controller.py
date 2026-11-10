import pytest
import requests

import directors.controller
import music.controller
from movie_prepopulate import controller

MOVIE = {
    "tconst": "tt0053472",
    "title": "Breathless",
    "year": "1960",
    "director": "Jean-Luc Godard",
}


@pytest.fixture
def stored_director(mongo):
    mongo["directors"].insert_one({"name": "Jean-Luc Godard", "bio": "Bio."})


@pytest.fixture
def stored_soundtrack(mongo):
    mongo["movie_soundtracks"].insert_one({"cache_key": "Breathless_1960"})


@pytest.fixture
def lookups(monkeypatch):
    """Replaces the director and soundtrack lookups, recording their arguments."""

    class Lookups:
        director_calls = []
        soundtrack_calls = []
        director = ({"name": "Jean-Luc Godard"}, 200)
        soundtrack = ({"tracks": []}, 200)

    def get_director_info(*args):
        Lookups.director_calls.append(args)
        return Lookups.director

    def get_movie_soundtrack(*args):
        Lookups.soundtrack_calls.append(args)
        return Lookups.soundtrack

    monkeypatch.setattr(controller, "get_director_info", get_director_info)
    monkeypatch.setattr(controller, "get_movie_soundtrack", get_movie_soundtrack)
    return Lookups


def test_movie_with_everything_stored_is_already_exists(
    stored_director, stored_soundtrack, lookups
):
    result = controller.prepopulate_movie_data(dict(MOVIE))

    assert result == {"status": "already_exists", "message": "Dados já existem"}
    assert lookups.director_calls == []
    assert lookups.soundtrack_calls == []


def test_missing_director_and_soundtrack_are_fetched(lookups):
    result = controller.prepopulate_movie_data(dict(MOVIE), "en")

    assert result["status"] == "success"
    assert result["results"] == {
        "director": {"name": "Jean-Luc Godard"},
        "soundtrack": {"tracks": []},
    }
    assert lookups.director_calls == [("Jean-Luc Godard", "tt0053472", "en")]
    assert lookups.soundtrack_calls == [("Breathless", "1960", "Jean-Luc Godard", "en")]


def test_only_the_missing_half_is_fetched(stored_director, lookups):
    result = controller.prepopulate_movie_data(dict(MOVIE))

    assert list(result["results"]) == ["soundtrack"]
    assert lookups.director_calls == []


def test_soundtrack_without_year_is_looked_up_by_title_only(mongo, lookups):
    mongo["movie_soundtracks"].insert_one({"cache_key": "Breathless"})
    mongo["directors"].insert_one({"name": "Jean-Luc Godard"})
    movie = {"title": "Breathless", "director": "Jean-Luc Godard"}

    assert controller.prepopulate_movie_data(movie)["status"] == "already_exists"


def test_both_lookups_failing_is_an_error(lookups):
    lookups.director = ({"error": "x"}, 500)
    lookups.soundtrack = ({"error": "x"}, 404)

    result = controller.prepopulate_movie_data(dict(MOVIE))

    assert result == {
        "status": "error",
        "message": "Não foi possível pré-popular os dados",
        "results": {},
    }


def test_answers_that_were_not_stored_do_not_count_as_populated(lookups):
    lookups.director = ({"name": "Jean-Luc Godard", "placeholder": True}, 200)
    lookups.soundtrack = ({"tracks": [], "source": "gpt"}, 200)

    assert controller.prepopulate_movie_data(dict(MOVIE))["status"] == "error"


def test_one_lookup_failing_is_still_a_success_with_the_other_half(lookups):
    lookups.soundtrack = ({"error": "x"}, 404)

    result = controller.prepopulate_movie_data(dict(MOVIE))

    assert result["status"] == "success"
    assert list(result["results"]) == ["director"]


def test_movie_without_director_is_already_exists_once_it_has_a_soundtrack(
    stored_soundtrack, lookups
):
    movie = {"title": "Breathless", "year": "1960"}

    result = controller.prepopulate_movie_data(movie)

    assert result["status"] == "already_exists"
    assert lookups.director_calls == []
    assert lookups.soundtrack_calls == []


def test_movie_without_director_only_looks_up_the_soundtrack(lookups):
    result = controller.prepopulate_movie_data({"title": "Breathless", "director": ""})

    assert result["status"] == "success"
    assert list(result["results"]) == ["soundtrack"]
    assert lookups.director_calls == []


def test_movie_without_title_is_an_error(lookups):
    result = controller.prepopulate_movie_data({"director": "Jean-Luc Godard"})

    assert result == {"status": "error", "message": "Erro: 'title'"}


def test_database_down_is_an_error_through_the_real_lookups(database_down):
    result = controller.prepopulate_movie_data(dict(MOVIE))

    assert result["status"] == "error"
    assert result["results"] == {}


def test_real_lookups_store_the_director(mongo, monkeypatch, fake_openai):
    def imdb_offline(url, **kwargs):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(directors.controller.requests, "get", imdb_offline)
    monkeypatch.setattr(directors.controller, "OpenAI", fake_openai(reply="Bio real."))
    monkeypatch.setattr(music.controller, "OPENAI_API_KEY", None)

    result = controller.prepopulate_movie_data(dict(MOVIE))

    assert result["status"] == "success"
    assert list(result["results"]) == ["director"]
    assert mongo["directors"].find_one({"name": "Jean-Luc Godard"})["bio"] == (
        "Bio real."
    )
    assert mongo["movie_soundtracks"].count_documents({}) == 0


def test_real_lookups_without_openai_populate_nothing(mongo, monkeypatch):
    monkeypatch.setattr(directors.controller, "OPENAI_API_KEY", None)
    monkeypatch.setattr(music.controller, "OPENAI_API_KEY", None)

    result = controller.prepopulate_movie_data({"title": "Breathless", "director": "X"})

    assert result["status"] == "error"
    assert mongo["directors"].count_documents({}) == 0


def test_prepopulate_all_counts_each_outcome(mongo, stored_director, lookups):
    mongo["movie_soundtracks"].insert_one({"cache_key": "Breathless_1960"})
    mongo["recommendations"].insert_many(
        [
            dict(MOVIE),
            {"tconst": "tt2", "title": "Cléo from 5 to 7", "director": "Agnès Varda"},
            {"tconst": "tt3", "director": "Nobody"},
        ]
    )

    result = controller.prepopulate_all_movies("en", max_workers=2)

    assert result["status"] == "completed"
    assert result["total_movies"] == 3
    assert result["already_exists_count"] == 1
    assert result["success_count"] == 1
    assert result["error_count"] == 1
    assert len(result["results"]) == 3
    assert sorted(lookups.director_calls) == [
        ("Agnès Varda", "tt2", "en"),
        ("Nobody", "tt3", "en"),
    ]


def test_prepopulate_all_with_no_movies_completes_with_zeroes(mongo):
    result = controller.prepopulate_all_movies()

    assert result == {
        "status": "completed",
        "total_movies": 0,
        "success_count": 0,
        "already_exists_count": 0,
        "error_count": 0,
        "results": [],
    }


def test_prepopulate_all_rejects_zero_workers(mongo):
    result = controller.prepopulate_all_movies(max_workers=0)

    assert result["status"] == "error"
    assert result["message"].startswith("Erro geral:")


def test_prepopulate_all_with_the_database_down_is_an_error(database_down):
    result = controller.prepopulate_all_movies()

    assert result["status"] == "error"
    assert result["message"].startswith("Erro geral:")


def test_stats_report_coverage_of_the_movies(mongo):
    mongo["recommendations"].insert_many(
        [
            {"tconst": "tt1", "title": "Breathless", "year": "1960", "director": "A"},
            {"tconst": "tt2", "title": "Contempt", "director": "A, B"},
            {"tconst": "tt3", "title": "Vagabond", "year": "1985", "director": "C"},
        ]
    )
    mongo["directors"].insert_many([{"name": "A"}, {"name": "B"}])
    mongo["movie_soundtracks"].insert_many(
        [{"cache_key": "Contempt"}, {"cache_key": "Vagabond"}]
    )

    assert controller.get_prepopulate_stats() == {
        "total_movies": 3,
        "total_directors": 2,
        "total_soundtracks": 2,
        # tt1 and tt2 have every director stored; tt3 does not.
        "director_coverage": 66.7,
        # Vagabond is stored without its year, so only Contempt matches.
        "soundtrack_coverage": 33.3,
        "overall_coverage": 50.0,
    }


def test_movie_with_several_directors_needs_all_of_them(mongo):
    mongo["recommendations"].insert_one({"title": "Fargo", "director": "Joel, Ethan"})
    mongo["directors"].insert_one({"name": "Joel"})

    assert controller.get_prepopulate_stats()["director_coverage"] == 0


def test_movie_without_director_counts_as_covered(mongo):
    mongo["recommendations"].insert_one({"title": "Anonymous"})

    assert controller.get_prepopulate_stats()["director_coverage"] == 100.0


def test_stats_without_movies_report_zero_coverage(mongo):
    mongo["directors"].insert_one({"name": "A"})

    stats = controller.get_prepopulate_stats()

    assert stats["total_directors"] == 1
    assert stats["director_coverage"] == 0
    assert stats["overall_coverage"] == 0


def test_coverage_never_exceeds_one_hundred_percent(mongo):
    mongo["recommendations"].insert_one({"title": "Breathless", "director": "A"})
    mongo["directors"].insert_many([{"name": "A"}, {"name": "B"}, {"name": "C"}])
    mongo["movie_soundtracks"].insert_many(
        [{"cache_key": "Breathless"}, {"cache_key": "Other"}]
    )

    stats = controller.get_prepopulate_stats()

    assert stats["director_coverage"] == 100.0
    assert stats["soundtrack_coverage"] == 100.0
    assert stats["overall_coverage"] == 100.0
    assert stats["total_directors"] == 3


def test_stats_with_the_database_down_return_an_error_payload(database_down):
    stats = controller.get_prepopulate_stats()

    assert list(stats) == ["error"]
    assert stats["error"].startswith("Erro ao buscar estatísticas:")


def test_single_movie_is_loaded_by_tconst_and_prepopulated(mongo, lookups):
    mongo["recommendations"].insert_one(dict(MOVIE))

    result = controller.prepopulate_single_movie("tt0053472", "en")

    assert result["status"] == "success"
    assert lookups.director_calls == [("Jean-Luc Godard", "tt0053472", "en")]


def test_single_unknown_movie_is_not_found(mongo, lookups):
    result = controller.prepopulate_single_movie("tt9")

    assert result == {"status": "not_found", "message": "Filme não encontrado"}
    assert lookups.soundtrack_calls == []


def test_single_movie_with_the_database_down_is_an_error(database_down):
    result = controller.prepopulate_single_movie("tt1")

    assert result["status"] == "error"
    assert result["message"].startswith("Erro:")
