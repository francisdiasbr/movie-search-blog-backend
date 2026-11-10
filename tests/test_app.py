"""The Flask app end to end: routing, query/body parsing and status codes."""

from datetime import datetime

import pytest
from botocore.exceptions import ClientError

import directors.controller
import directors.routes
import movie_detail_cache.controller
import movie_prepopulate.controller
import music.controller
import music.routes
from app import app


@pytest.fixture
def client():
    return app.test_client()


@pytest.fixture
def no_openai(monkeypatch):
    """Controllers behave as if no OpenAI key were configured."""
    monkeypatch.setattr(directors.controller, "OPENAI_API_KEY", None)
    monkeypatch.setattr(music.controller, "OPENAI_API_KEY", None)


@pytest.fixture
def prepopulate(monkeypatch):
    calls = []

    def prepopulate_movie_data(movie, language):
        calls.append((movie["tconst"], language))
        return {"status": "success", "results": {}}

    monkeypatch.setattr(
        movie_prepopulate.controller, "prepopulate_movie_data", prepopulate_movie_data
    )
    return calls


class FakeS3:
    def __init__(self, keys=(), error=None):
        self.keys = list(keys)
        self.error = error
        self.buckets = []

    def list_objects_v2(self, **kwargs):
        self.buckets.append(kwargs["Bucket"])
        if self.error:
            raise self.error
        contents = [
            {"Key": key, "LastModified": datetime(2024, 1, n + 1)}
            for n, key in enumerate(self.keys)
            if key.startswith(kwargs["Prefix"])
        ]
        return {"Contents": contents} if contents else {}

    def get_object_tagging(self, **kwargs):
        self.buckets.append(kwargs["Bucket"])
        if self.error:
            raise self.error
        return {"TagSet": [{"Key": "subtitle_pt", "Value": "Legenda"}]}


@pytest.fixture
def s3(monkeypatch):
    def install(**kwargs):
        fake = FakeS3(**kwargs)
        monkeypatch.setattr("boto3.client", lambda *a, **kw: fake)
        return fake

    return install


def test_root_health_route_is_shadowed_by_the_restx_root(client):
    """Current behaviour: `Api(app)` claims "/" first, so `home` never runs."""
    response = client.get("/")
    endpoints = [rule.endpoint for rule in app.url_map.iter_rules() if rule.rule == "/"]

    assert response.status_code == 404
    assert endpoints == ["root", "home"]


def test_root_health_view_reports_the_api_online():
    with app.test_request_context("/"):
        response = app.view_functions["home"]()

    assert response.json["status"] == "online"
    assert response.json["docs"] == "/docs"


def test_swagger_documents_every_namespace(client):
    docs = client.get("/docs")
    spec = client.get("/swagger.json")
    paths = spec.json["paths"]

    assert docs.status_code == 200
    for prefix in [
        "/api/home",
        "/api/directors",
        "/api/favorites",
        "/api/generate-blogpost",
        "/api/images",
        "/api/movie-detail",
        "/api/prepopulate",
        "/api/music",
        "/api/personal-opinion",
        "/api/recommendations",
        "/api/write-review",
    ]:
        assert any(path.startswith(prefix + "/") for path in paths), prefix


def test_unknown_route_is_404(client):
    assert client.get("/api/nothing-here").status_code == 404


def test_cors_allows_any_origin(client):
    response = client.get("/docs", headers={"Origin": "https://blog.example"})

    assert response.headers["Access-Control-Allow-Origin"] == "https://blog.example"


# --- favorites ---------------------------------------------------------------


def test_favorites_search_parses_the_body(client, mongo):
    mongo["favoritelist"].insert_many(
        [
            {"tconst": "tt1", "primaryTitle": "Breathless", "country": "France"},
            {"tconst": "tt2", "primaryTitle": "Contempt", "country": "France"},
            {"tconst": "tt3", "primaryTitle": "8½", "country": "Italy"},
        ]
    )

    response = client.post(
        "/api/favorites/search",
        json={"filters": {"country": "France"}, "page": "2", "page_size": "1"},
    )

    assert response.status_code == 200
    assert [e["tconst"] for e in response.json["entries"]] == ["tt1"]
    assert response.json["total_pages"] == 2
    assert response.json["current_page"] == 2


def test_favorites_search_with_no_results_is_404(client):
    response = client.post("/api/favorites/search", json={"search_term": "x"})

    assert response.status_code == 404
    assert response.json["entries"] == []


def test_favorites_search_rejects_a_non_object_body(client):
    response = client.post("/api/favorites/search", json=["tt1"])

    assert response.status_code == 400
    assert response.json == {"status": 400, "message": "Dados de entrada inválidos"}


@pytest.mark.parametrize(
    "request_kwargs",
    [
        {"json": {"page": "two"}},
        {"json": {"page_size": 0}},
        {"data": "tt1", "content_type": "text/plain"},
    ],
)
def test_favorites_search_turns_client_mistakes_into_500(client, request_kwargs):
    """Current behaviour: bad paging and a non-JSON body are not 400/415."""
    response = client.post("/api/favorites/search", **request_kwargs)

    assert response.status_code == 500
    assert response.json["message"] == "Erro interno do servidor"


def test_favorites_search_with_the_database_down_is_500(client, database_down):
    response = client.post("/api/favorites/search", json={})

    assert response.status_code == 500
    assert response.json["error"] == "Collection not found"


# --- generate-blogpost -------------------------------------------------------


def test_blogpost_search_and_fetch(client, mongo):
    mongo["blogposts"].insert_one({"tconst": "tt1", "primaryTitle": "Breathless"})

    found = client.post(
        "/api/generate-blogpost/search", json={"filters": {"primaryTitle": "breath"}}
    )
    missing = client.post(
        "/api/generate-blogpost/search", json={"filters": {"primaryTitle": "zzz"}}
    )
    post = client.get("/api/generate-blogpost/tt1")
    unknown = client.get("/api/generate-blogpost/tt9")

    assert found.status_code == 200
    assert found.json["total_documents"] == 1
    assert missing.status_code == 404
    assert post.status_code == 200
    assert post.json["data"]["primaryTitle"] == "Breathless"
    assert unknown.status_code == 404


def test_blogpost_search_rejects_bad_bodies(client):
    not_an_object = client.post("/api/generate-blogpost/search", json=[1])
    not_json = client.post(
        "/api/generate-blogpost/search", data="x", content_type="text/plain"
    )

    assert not_an_object.status_code == 400
    assert not_json.status_code == 415


# --- home --------------------------------------------------------------------


def test_home_cards_route_returns_cards_with_images(client, mongo, s3):
    mongo["authoralreviewslist"].insert_many(
        [
            {"tconst": "tt1", "primaryTitle": "Breathless", "created_at": "2024"},
            {"tconst": "tt2", "primaryTitle": "Contempt", "created_at": "2024"},
        ]
    )
    s3(keys=["tt1/a.jpg"])

    response = client.post(
        "/api/home/cards", json={"filters": {"primaryTitle": "breath"}}
    )

    assert response.status_code == 200
    assert response.json["total_documents"] == 1
    assert response.json["entries"][0]["imageUrl"] == (
        "https://test-bucket.s3.us-east-2.amazonaws.com/tt1/a.jpg"
    )


def test_home_cards_with_no_reviews_is_500(client, s3):
    """Current behaviour: an empty blog breaks the home page (see controller)."""
    s3()

    response = client.post("/api/home/cards", json={})

    assert response.status_code == 500
    assert response.json == {"status": 500, "message": "Erro ao buscar cards"}


def test_home_cards_with_a_datetime_created_at_is_500(client, mongo, s3):
    """Current behaviour: a BSON date in created_at cannot be serialised."""
    mongo["authoralreviewslist"].insert_one(
        {"tconst": "tt1", "created_at": datetime(2024, 1, 1)}
    )
    s3()

    response = client.post("/api/home/cards", json={})

    assert response.status_code == 500


def test_home_cards_without_a_json_body_is_415(client):
    assert client.post("/api/home/cards").status_code == 415


def test_home_cards_with_the_database_down_is_500(client, database_down):
    response = client.post("/api/home/cards", json={})

    assert response.status_code == 500
    assert response.json["message"] == "Banco de dados indisponível"


# --- images ------------------------------------------------------------------


def test_images_routes_use_the_configured_bucket(client, s3):
    fake = s3(keys=["tt1/b.jpg", "tt1/a.jpg", "tt2/z.jpg"])

    listing = client.get("/api/images/tt1")
    single = client.get("/api/images/tt1/a.jpg")

    assert listing.status_code == 200
    assert [i["filename"] for i in listing.json["images"]] == ["b.jpg", "a.jpg"]
    assert listing.json["images"][0]["subtitle_pt"] == "Legenda"
    assert single.status_code == 200
    assert single.json["url"].endswith("/tt1/a.jpg")
    assert set(fake.buckets) == {"test-bucket"}


def test_images_route_without_images_is_200_not_404(client, s3):
    """Current behaviour: the documented 404 is never returned."""
    s3()

    response = client.get("/api/images/tt9")

    assert response.status_code == 200
    assert response.json == {"images": []}


def test_images_routes_report_s3_failures_as_500(client, s3):
    s3(error=ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObjectTagging"))

    assert client.get("/api/images/tt1").status_code == 500
    assert client.get("/api/images/tt1/a.jpg").status_code == 500


# --- personal-opinion --------------------------------------------------------


def test_personal_opinion_routes(client, mongo):
    mongo["personal_opinions"].insert_many(
        [
            {"tconst": "tt1", "opinion": "Loved it", "enjoying_1": "a"},
            {"tconst": "tt2", "opinion": "Hated it", "enjoying_1": "b"},
        ]
    )

    everything = client.get("/api/personal-opinion/")
    search = client.post(
        "/api/personal-opinion/", json={"filters": {"opinion": "loved"}}
    )
    one = client.get("/api/personal-opinion/tt2")
    unknown = client.get("/api/personal-opinion/tt9")

    assert everything.status_code == 200
    assert len(everything.json["data"]) == 2
    assert [o["tconst"] for o in search.json["entries"]] == ["tt1"]
    assert one.json["data"]["opinion"] == "Hated it"
    assert unknown.status_code == 404


def test_personal_opinion_update_route(client, mongo):
    mongo["personal_opinions"].insert_one({"tconst": "tt1", "opinion": "Loved it"})

    updated = client.put("/api/personal-opinion/tt1", json={"opinion": "Adored it"})
    unchanged = client.put("/api/personal-opinion/tt1", json={"opinion": "Adored it"})
    unknown = client.put("/api/personal-opinion/tt9", json={"opinion": "x"})
    not_an_object = client.put("/api/personal-opinion/tt1", json=["x"])

    assert updated.status_code == 200
    assert mongo["personal_opinions"].find_one({})["opinion"] == "Adored it"
    assert unchanged.status_code == 400
    assert unknown.status_code == 404
    assert not_an_object.status_code == 400


def test_personal_opinion_search_rejects_a_non_object_body(client):
    assert client.post("/api/personal-opinion/", json="x").status_code == 400


def test_personal_opinion_with_the_database_down_is_500(client, database_down):
    assert client.get("/api/personal-opinion/").status_code == 500
    assert client.get("/api/personal-opinion/tt1").status_code == 500


# --- write-review ------------------------------------------------------------


def test_write_review_routes(client, mongo):
    mongo["authoralreviewslist"].insert_many(
        [
            {"tconst": "tt1", "primaryTitle": "Breathless"},
            {"tconst": "tt2", "primaryTitle": "Contempt"},
        ]
    )

    one = client.get("/api/write-review/tt1")
    unknown = client.get("/api/write-review/tt9")
    search = client.post("/api/write-review/search", json={"page": 2, "page_size": 1})

    assert one.status_code == 200
    assert one.json["data"]["primaryTitle"] == "Breathless"
    assert unknown.status_code == 404
    assert search.status_code == 200
    assert search.json["total_documents"] == 2
    assert [r["tconst"] for r in search.json["entries"]] == ["tt1"]


def test_write_review_search_is_a_static_route_not_a_tconst(client, mongo):
    """GET on /search falls into the tconst route and finds no such review."""
    assert client.get("/api/write-review/search").status_code == 404


# --- directors ---------------------------------------------------------------


def test_director_routes_round_trip(client, mongo, no_openai):
    created = client.get("/api/directors/Agnès Varda")
    listed = client.get("/api/directors/all")
    deleted = client.delete("/api/directors/Agnès Varda")
    deleted_again = client.delete("/api/directors/Agnès Varda")

    assert created.status_code == 200
    assert created.json["bio"] == "Diretor de cinema conhecido por Agnès Varda."
    assert [d["name"] for d in listed.json["directors"]] == ["Agnès Varda"]
    assert deleted.status_code == 200
    assert deleted_again.status_code == 404


@pytest.mark.parametrize(
    "query, expected",
    [
        ("", ("Agnès Varda", None, "pt")),
        ("?tconst=tt1&language=en", ("Agnès Varda", "tt1", "en")),
        ("?language=fr", ("Agnès Varda", None, "pt")),
    ],
)
def test_director_route_reads_tconst_and_normalises_the_language(
    client, monkeypatch, query, expected
):
    received = []

    def get_director_info(*args):
        received.append(args)
        return {"name": args[0]}, 200

    monkeypatch.setattr(directors.routes, "get_director_info", get_director_info)

    response = client.get(f"/api/directors/Agnès Varda{query}")

    assert response.status_code == 200
    assert received == [expected]


def test_director_route_with_the_database_down_is_500(client, database_down):
    response = client.get("/api/directors/Agnès Varda")

    assert response.status_code == 500
    assert response.json == {"error": "Erro ao buscar informações do diretor"}


# --- music -------------------------------------------------------------------


def test_soundtrack_routes_round_trip(client, mongo):
    mongo["movie_soundtracks"].insert_one(
        {"cache_key": "Breathless_1960", "description": "Jazz.", "tracks": []}
    )

    found = client.get("/api/music/soundtrack?title=Breathless&year=1960")
    listed = client.get("/api/music/all")
    wrong_year = client.delete("/api/music/soundtrack?title=Breathless")
    deleted = client.delete("/api/music/soundtrack?title=Breathless&year=1960")

    assert found.status_code == 200
    assert found.json["description"] == "Jazz."
    assert listed.json["soundtracks"][0]["cache_key"] == "Breathless_1960"
    assert wrong_year.status_code == 404
    assert deleted.status_code == 200
    assert mongo["movie_soundtracks"].count_documents({}) == 0


def test_soundtrack_routes_require_a_title(client):
    get = client.get("/api/music/soundtrack?year=1960")
    delete = client.delete("/api/music/soundtrack")

    assert get.status_code == 400
    assert get.json == {"error": "Título do filme é obrigatório"}
    assert delete.status_code == 400


@pytest.mark.parametrize(
    "query, expected",
    [
        ("title=Breathless", ("Breathless", None, None, "pt")),
        (
            "title=Breathless&year=1960&director=Godard&language=en",
            ("Breathless", 1960, "Godard", "en"),
        ),
        ("title=Breathless&year=sixty&language=de", ("Breathless", None, None, "pt")),
    ],
)
def test_soundtrack_route_parses_the_query_string(client, monkeypatch, query, expected):
    received = []

    def get_movie_soundtrack(*args):
        received.append(args)
        return {"tracks": []}, 200

    monkeypatch.setattr(music.routes, "get_movie_soundtrack", get_movie_soundtrack)

    response = client.get(f"/api/music/soundtrack?{query}")

    assert response.status_code == 200
    assert received == [expected]


def test_unknown_soundtrack_without_openai_is_404(client, no_openai):
    response = client.get("/api/music/soundtrack?title=Breathless&language=en")

    assert response.status_code == 404
    assert response.json == {"error": "Could not find movie soundtrack"}


# --- movie-detail ------------------------------------------------------------


@pytest.fixture
def cacheable_movie(mongo):
    mongo["recommendations"].insert_one(
        {"tconst": "tt1", "title": "Breathless", "year": "1960", "director": "Godard"}
    )
    mongo["directors"].insert_one({"name": "Godard", "bio": "Bio."})
    mongo["movie_soundtracks"].insert_one({"cache_key": "Breathless_1960"})


def test_movie_detail_route_always_fails_to_serialise_its_answer(
    client, mongo, cacheable_movie
):
    """Current behaviour: `created_at` is a datetime, so every hit is a 500.

    The cache document is written anyway, and the cached read fails the same way.
    """
    first = client.get("/api/movie-detail/tt1")
    cached = client.get("/api/movie-detail/tt1?language=pt")

    assert first.status_code == 500
    assert cached.status_code == 500
    assert mongo["movie_detail_cache"].count_documents({"cache_key": "tt1_pt"}) == 1


def test_movie_detail_route_for_an_unknown_movie_is_404(client):
    response = client.get("/api/movie-detail/tt9")

    assert response.status_code == 404
    assert response.json == {"error": "Filme não encontrado"}


def test_movie_detail_maintenance_routes(client, mongo, cacheable_movie, monkeypatch):
    monkeypatch.setattr(movie_detail_cache.controller, "OPENAI_API_KEY", None)
    client.get("/api/movie-detail/tt1")
    client.get("/api/movie-detail/tt1?language=en")

    stats = client.get("/api/movie-detail/stats")
    one = client.post("/api/movie-detail/tt1/invalidate", json={"language": "en"})
    after_one = mongo["movie_detail_cache"].count_documents({})
    every = client.post("/api/movie-detail/tt1/invalidate", json={})
    cleanup = client.post("/api/movie-detail/cleanup")

    assert stats.status_code == 200
    assert stats.json["total_caches"] == 2
    assert stats.json["valid_caches"] == 2
    assert one.status_code == 200
    assert after_one == 1
    assert every.status_code == 200
    assert mongo["movie_detail_cache"].count_documents({}) == 0
    assert cleanup.json == {"message": "0 caches expirados removidos"}


def test_movie_detail_invalidate_requires_a_json_body(client):
    """Current behaviour: a POST without a body is rejected with 415."""
    assert client.post("/api/movie-detail/tt1/invalidate").status_code == 415


def test_movie_detail_with_the_database_down_is_500(client, database_down):
    assert client.get("/api/movie-detail/tt1").status_code == 500
    assert client.get("/api/movie-detail/stats").status_code == 500


# --- prepopulate -------------------------------------------------------------


def test_prepopulate_stats_route(client, mongo):
    mongo["recommendations"].insert_one({"tconst": "tt1"})
    mongo["directors"].insert_one({"name": "Godard"})

    response = client.get("/api/prepopulate/stats")

    assert response.status_code == 200
    assert response.json["director_coverage"] == 100.0
    assert response.json["overall_coverage"] == 50.0


def test_prepopulate_stats_with_the_database_down_is_still_200(client, database_down):
    """Current behaviour: the error payload goes out with the default status."""
    response = client.get("/api/prepopulate/stats")

    assert response.status_code == 200
    assert "error" in response.json


def test_prepopulate_movie_route(client, mongo, no_openai):
    payload = {"title": "Breathless", "director": "Jean-Luc Godard", "language": "en"}

    first = client.post("/api/prepopulate/movie", json=payload)
    empty = client.post("/api/prepopulate/movie", json={})
    no_title = client.post("/api/prepopulate/movie", json={"director": "X"})

    assert first.status_code == 200
    assert first.json["status"] == "success"
    assert first.json["results"]["director"]["bio"] == (
        "Film director known for Jean-Luc Godard."
    )
    assert empty.status_code == 400
    assert no_title.status_code == 500


def test_prepopulate_single_route(client, mongo, no_openai):
    mongo["recommendations"].insert_one(
        {"tconst": "tt1", "title": "Breathless", "director": "Godard"}
    )
    mongo["directors"].insert_one({"name": "Godard"})
    mongo["movie_soundtracks"].insert_one({"cache_key": "Breathless"})

    known = client.post("/api/prepopulate/tt1", json={})
    unknown = client.post("/api/prepopulate/tt9", json={})

    assert known.status_code == 200
    assert known.json["status"] == "already_exists"
    # Current behaviour: the documented 404 is returned as 500.
    assert unknown.status_code == 500
    assert unknown.json == {"status": "error", "message": "Filme não encontrado"}


def test_prepopulate_all_route(client, mongo, no_openai):
    mongo["recommendations"].insert_one(
        {"title": "Breathless", "director": "Jean-Luc Godard"}
    )

    done = client.post("/api/prepopulate/all", json={"max_workers": 1})
    bad_workers = client.post("/api/prepopulate/all", json={"max_workers": 0})

    assert done.status_code == 200
    assert done.json["total_movies"] == 1
    assert done.json["success_count"] == 1
    assert mongo["directors"].count_documents({}) == 1
    assert bad_workers.status_code == 500
    assert bad_workers.json["status"] == "error"


# --- recommendations ---------------------------------------------------------


def test_recommendation_listing_routes(client, mongo):
    mongo["recommendations"].insert_many(
        [
            {"tconst": "tt1", "title": "Breathless", "position": 1},
            {"tconst": "tt2", "title": "Contempt", "position": 2},
            {"tconst": "tt3", "title": "Vagabond", "position": 3},
        ]
    )

    everything = client.get("/api/recommendations/random")
    page = client.get("/api/recommendations/all?page=2&page_size=2")
    search = client.get("/api/recommendations/all?search_term=contempt&language=xx")

    assert everything.json["total"] == 3
    assert [r["tconst"] for r in page.json["entries"]] == ["tt3"]
    assert [r["tconst"] for r in search.json["entries"]] == ["tt2"]


def test_recommendation_add_route(client, mongo, prepopulate):
    created = client.post(
        "/api/recommendations/add?language=en", json={"tconst": "tt1", "title": "A"}
    )
    duplicate = client.post("/api/recommendations/add", json={"tconst": "tt1"})
    empty = client.post("/api/recommendations/add", json={})

    assert created.status_code == 201
    assert created.json["movie"]["position"] == 1
    assert prepopulate == [("tt1", "en")]
    assert duplicate.status_code == 400
    assert empty.status_code == 400
    assert empty.json == {"error": "Dados do filme são obrigatórios"}


def test_prepopulate_false_in_the_query_string_is_still_true(client, prepopulate):
    """Current behaviour: `type=bool` turns any non-empty string into True."""
    client.post("/api/recommendations/add?prepopulate=false", json={"tconst": "tt1"})
    client.post("/api/recommendations/bulk-add?prepopulate=0", json=[{"tconst": "tt2"}])
    client.post("/api/recommendations/add?prepopulate=", json={"tconst": "tt3"})

    assert prepopulate == [("tt1", "pt"), ("tt2", "pt")]


def test_recommendation_bulk_add_route(client, mongo, prepopulate):
    mongo["recommendations"].insert_one({"tconst": "tt1", "position": 7})

    created = client.post(
        "/api/recommendations/bulk-add", json=[{"tconst": "tt1"}, {"tconst": "tt2"}]
    )
    all_known = client.post("/api/recommendations/bulk-add", json=[{"tconst": "tt1"}])
    not_a_list = client.post("/api/recommendations/bulk-add", json={"tconst": "tt3"})
    empty = client.post("/api/recommendations/bulk-add", json=[])

    assert created.status_code == 201
    assert created.json["skipped"] == 1
    assert created.json["movies"][0]["position"] == 8
    assert all_known.status_code == 400
    assert not_a_list.status_code == 400
    assert not_a_list.json == {"error": "Lista de filmes é obrigatória"}
    assert empty.status_code == 400


def test_recommendation_delete_routes(client, mongo):
    mongo["recommendations"].insert_many(
        [{"tconst": "tt1"}, {"tconst": "tt2"}, {"tconst": "clear"}]
    )

    one = client.delete("/api/recommendations/tt1")
    unknown = client.delete("/api/recommendations/tt9")
    remaining = mongo["recommendations"].count_documents({})
    everything = client.delete("/api/recommendations/clear")

    assert one.status_code == 200
    assert unknown.status_code == 404
    assert remaining == 2
    # /clear wins over /<tconst>: it wipes the collection.
    assert everything.json == {"data": "2 recommendations deleted"}


def test_recommendations_with_the_database_down_are_500(client, database_down):
    assert client.get("/api/recommendations/random").status_code == 500
    assert client.get("/api/recommendations/all").status_code == 500
    assert client.delete("/api/recommendations/tt1").status_code == 500
    assert (
        client.post(
            "/api/recommendations/add?prepopulate=", json={"tconst": "tt1"}
        ).status_code
        == 500
    )
