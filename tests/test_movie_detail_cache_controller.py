from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
import requests

import directors.controller
import music.controller
from movie_detail_cache import controller

MOVIE = {
    "tconst": "tt0053472",
    "title": "Breathless",
    "year": "1960",
    "director": "Jean-Luc Godard",
    "position": 1,
}


@pytest.fixture
def caches(mongo):
    return mongo["movie_detail_cache"]


@pytest.fixture
def movie(mongo):
    mongo["recommendations"].insert_one(dict(MOVIE))


@pytest.fixture
def stored_director(mongo):
    mongo["directors"].insert_one(
        {"name": "Jean-Luc Godard", "bio": "Cineasta franco-suíço.", "photo": "g.jpg"}
    )


@pytest.fixture
def stored_soundtrack(mongo):
    mongo["movie_soundtracks"].insert_one(
        {"cache_key": "Breathless_1960", "description": "Jazz francês.", "tracks": []}
    )


@pytest.fixture
def lookups(monkeypatch):
    """Replaces the director and soundtrack lookups, recording their arguments."""
    calls = {"director": [], "soundtrack": []}
    answers = {
        "director": ({"name": "Jean-Luc Godard", "bio": "Fetched bio."}, 200),
        "soundtrack": ({"description": "Fetched soundtrack.", "tracks": []}, 200),
    }

    def get_director_info(*args):
        calls["director"].append(args)
        return answers["director"]

    def get_movie_soundtrack(*args):
        calls["soundtrack"].append(args)
        return answers["soundtrack"]

    monkeypatch.setattr(controller, "get_director_info", get_director_info)
    monkeypatch.setattr(controller, "get_movie_soundtrack", get_movie_soundtrack)
    return SimpleNamespace(calls=calls, answers=answers)


def test_fresh_cache_is_served_as_is(caches):
    caches.insert_one(
        {
            "cache_key": "tt0053472_pt",
            "movie_id": "tt0053472",
            "movie": {"title": "Cached"},
            "created_at": datetime.now() - timedelta(hours=2),
            "from_cache": False,
        }
    )

    body, status = controller.get_movie_detail_cache("tt0053472")

    assert status == 200
    assert body["movie"] == {"title": "Cached"}
    assert body["from_cache"] is True
    assert body["cache_age_hours"] == pytest.approx(2, abs=0.01)
    assert isinstance(body["_id"], str)
    assert caches.count_documents({}) == 1


def test_cache_is_built_from_the_stored_director_and_soundtrack(
    caches, movie, stored_director, stored_soundtrack
):
    body, status = controller.get_movie_detail_cache("tt0053472")

    assert status == 200
    assert body["cache_key"] == "tt0053472_pt"
    assert body["movie_id"] == "tt0053472"
    assert body["language"] == "pt"
    assert body["from_cache"] is False
    assert body["movie"]["title"] == "Breathless"
    assert body["director"]["bio"] == "Cineasta franco-suíço."
    assert body["soundtrack"]["description"] == "Jazz francês."
    assert datetime.fromisoformat(body["created_at"])
    assert isinstance(body["_id"], str)
    assert isinstance(body["director"]["_id"], str)

    stored = caches.find_one({"cache_key": "tt0053472_pt"})
    assert isinstance(stored["created_at"], datetime)
    assert stored["movie"]["tconst"] == "tt0053472"
    assert stored["soundtrack"]["tracks"] == []


def test_second_request_comes_from_the_cache(
    caches, movie, stored_director, stored_soundtrack
):
    controller.get_movie_detail_cache("tt0053472")

    body, status = controller.get_movie_detail_cache("tt0053472")

    assert status == 200
    assert body["from_cache"] is True
    assert caches.count_documents({}) == 1


def test_each_language_has_its_own_cache_entry(
    caches, movie, stored_director, stored_soundtrack, monkeypatch
):
    monkeypatch.setattr(controller, "OPENAI_API_KEY", None)

    controller.get_movie_detail_cache("tt0053472", "pt")
    controller.get_movie_detail_cache("tt0053472", "en")

    assert sorted(c["cache_key"] for c in caches.find()) == [
        "tt0053472_en",
        "tt0053472_pt",
    ]


def test_expired_cache_is_replaced(caches, movie, stored_director, stored_soundtrack):
    caches.insert_one(
        {
            "cache_key": "tt0053472_pt",
            "movie_id": "tt0053472",
            "movie": {"title": "Stale"},
            "created_at": datetime.now() - timedelta(hours=25),
        }
    )

    body, status = controller.get_movie_detail_cache("tt0053472")

    assert status == 200
    assert body["from_cache"] is False
    assert body["movie"]["title"] == "Breathless"
    assert [c["movie"]["title"] for c in caches.find()] == ["Breathless"]


def test_cache_with_a_non_datetime_timestamp_is_rebuilt_but_not_removed(
    caches, movie, stored_director, stored_soundtrack
):
    """Current behaviour: the unreadable entry stays, so the key is duplicated."""
    caches.insert_one({"cache_key": "tt0053472_pt", "created_at": "2024-01-01"})

    body, status = controller.get_movie_detail_cache("tt0053472")

    assert status == 200
    assert body["from_cache"] is False
    assert caches.count_documents({"cache_key": "tt0053472_pt"}) == 2


def test_unknown_movie_is_404_and_nothing_is_cached(caches, movie):
    body, status = controller.get_movie_detail_cache("tt9999999")

    assert status == 404
    assert body == {"error": "Filme não encontrado"}
    assert caches.count_documents({}) == 0


def test_movie_id_also_matches_title_and_director_text(
    caches, mongo, movie, stored_director, stored_soundtrack
):
    """Current behaviour: the id goes through the recommendations search term."""
    mongo["recommendations"].insert_one(
        {"tconst": "tt2", "title": "Contempt", "director": "Godard", "position": 2}
    )

    body, status = controller.get_movie_detail_cache("godard")

    assert status == 200
    assert body["movie"]["tconst"] == "tt0053472"
    assert body["cache_key"] == "godard_pt"


def test_missing_director_and_soundtrack_are_fetched(caches, movie, lookups):
    body, status = controller.get_movie_detail_cache("tt0053472", "en")

    assert status == 200
    assert body["director"] == {"name": "Jean-Luc Godard", "bio": "Fetched bio."}
    assert body["soundtrack"]["description"] == "Fetched soundtrack."
    assert lookups.calls["director"] == [("Jean-Luc Godard", "tt0053472", "en")]
    assert lookups.calls["soundtrack"] == [
        ("Breathless", "1960", "Jean-Luc Godard", "en")
    ]
    assert caches.find_one({})["director"]["bio"] == "Fetched bio."


def test_stored_data_skips_the_lookups(
    caches, movie, stored_director, stored_soundtrack, lookups
):
    controller.get_movie_detail_cache("tt0053472")

    assert lookups.calls == {"director": [], "soundtrack": []}


def test_failed_lookups_are_cached_as_null(caches, movie, lookups):
    """Current behaviour: a failed lookup is frozen in the cache for 24 hours."""
    lookups.answers["director"] = ({"error": "x"}, 500)
    lookups.answers["soundtrack"] = ({"error": "x"}, 404)

    body, status = controller.get_movie_detail_cache("tt0053472")

    assert status == 200
    assert body["director"] is None
    assert body["soundtrack"] is None
    assert caches.find_one({})["soundtrack"] is None


def test_movie_without_director_does_not_look_one_up(caches, mongo, lookups):
    mongo["recommendations"].insert_one({"tconst": "tt5", "title": "Anonymous"})

    body, status = controller.get_movie_detail_cache("tt5")

    assert status == 200
    assert body["director"] is None
    assert lookups.calls["director"] == []
    assert lookups.calls["soundtrack"] == [("Anonymous", None, None, "pt")]


def test_build_runs_the_real_lookups_end_to_end(caches, mongo, movie, monkeypatch):
    def imdb_offline(url, **kwargs):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(directors.controller.requests, "get", imdb_offline)
    monkeypatch.setattr(directors.controller, "OPENAI_API_KEY", None)
    monkeypatch.setattr(music.controller, "OPENAI_API_KEY", None)

    body, status = controller.get_movie_detail_cache("tt0053472")

    assert status == 200
    assert body["director"]["bio"] == "Diretor de cinema conhecido por Jean-Luc Godard."
    assert body["soundtrack"] is None
    assert mongo["directors"].count_documents({"name": "Jean-Luc Godard"}) == 1


def test_english_cache_translates_the_stored_texts(
    caches, mongo, movie, stored_director, stored_soundtrack, monkeypatch, fake_openai
):
    fake = fake_openai(reply=" Translated. ")
    monkeypatch.setattr("openai.OpenAI", fake)

    body, status = controller.get_movie_detail_cache("tt0053472", "en")

    assert status == 200
    assert body["director"]["bio"] == "Translated."
    assert body["soundtrack"]["description"] == "Translated."
    assert "Cineasta franco-suíço." in fake.prompts[0]
    assert "Jazz francês." in fake.prompts[1]
    assert fake.api_keys == ["fake-openai-key", "fake-openai-key"]
    # The source documents stay in Portuguese.
    assert mongo["directors"].find_one({})["bio"] == "Cineasta franco-suíço."


def test_translation_failure_keeps_the_stored_texts(
    caches, movie, stored_director, stored_soundtrack, monkeypatch, fake_openai
):
    monkeypatch.setattr("openai.OpenAI", fake_openai(error=TimeoutError()))

    body, status = controller.get_movie_detail_cache("tt0053472", "en")

    assert status == 200
    assert body["director"]["bio"] == "Cineasta franco-suíço."
    assert body["soundtrack"]["description"] == "Jazz francês."


def test_movie_without_title_is_500(caches, mongo):
    mongo["recommendations"].insert_one({"tconst": "tt5"})

    body, status = controller.get_movie_detail_cache("tt5")

    assert status == 500
    assert body == {"error": "Erro ao criar cache de detalhes do filme"}


def test_database_down_is_500(database_down):
    body, status = controller.get_movie_detail_cache("tt0053472")

    assert status == 500
    assert body == {"error": "Erro ao buscar cache de detalhes do filme"}


@pytest.fixture
def mixed_caches(caches):
    now = datetime.now()
    caches.insert_many(
        [
            {
                "cache_key": "tt1_pt",
                "movie_id": "tt1",
                "language": "pt",
                "created_at": now,
            },
            {
                "cache_key": "tt1_en",
                "movie_id": "tt1",
                "language": "en",
                "created_at": now - timedelta(hours=30),
            },
            {
                "cache_key": "tt2_pt",
                "movie_id": "tt2",
                "language": "pt",
                "created_at": now - timedelta(hours=1),
            },
        ]
    )
    return caches


def test_invalidate_one_language(mixed_caches):
    body, status = controller.invalidate_movie_cache("tt1", "en")

    assert status == 200
    assert body == {"message": "Cache invalidado para filme tt1"}
    assert sorted(c["cache_key"] for c in mixed_caches.find()) == ["tt1_pt", "tt2_pt"]


def test_invalidate_every_language_of_a_movie(mixed_caches):
    controller.invalidate_movie_cache("tt1")

    assert [c["cache_key"] for c in mixed_caches.find()] == ["tt2_pt"]


def test_invalidate_is_200_even_when_nothing_was_cached(mixed_caches):
    body, status = controller.invalidate_movie_cache("tt9")

    assert status == 200
    assert mixed_caches.count_documents({}) == 3


def test_invalidate_with_the_database_down_is_500(database_down):
    assert controller.invalidate_movie_cache("tt1") == (
        {"error": "Erro ao invalidar cache"},
        500,
    )


def test_stats_split_valid_and_expired_and_rank_languages(mixed_caches):
    body, status = controller.get_cache_stats()

    assert status == 200
    assert body == {
        "total_caches": 3,
        "valid_caches": 2,
        "expired_caches": 1,
        "language_stats": [{"_id": "pt", "count": 2}, {"_id": "en", "count": 1}],
    }


def test_stats_on_an_empty_cache(caches):
    body, status = controller.get_cache_stats()

    assert status == 200
    assert body == {
        "total_caches": 0,
        "valid_caches": 0,
        "expired_caches": 0,
        "language_stats": [],
    }


def test_stats_with_the_database_down_is_500(database_down):
    assert controller.get_cache_stats()[1] == 500


def test_cleanup_removes_only_the_expired_entries(mixed_caches):
    body, status = controller.cleanup_expired_cache()

    assert status == 200
    assert body == {"message": "1 caches expirados removidos"}
    assert sorted(c["cache_key"] for c in mixed_caches.find()) == ["tt1_pt", "tt2_pt"]


def test_cleanup_with_the_database_down_is_500(database_down):
    assert controller.cleanup_expired_cache()[1] == 500
