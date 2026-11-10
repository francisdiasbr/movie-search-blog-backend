import json

import pytest

from music import controller

GPT_TRACKS = {
    "tracks": [
        {
            "title": "New York Herald Tribune",
            "artist": "Martial Solal",
            "description": "Tema",
        },
        {"title": "L'amour, la mort", "artist": "Martial Solal"},
    ],
    "description": "Jazz francês.",
}

SPOTIFY_TRACK = {
    "name": "New York Herald Tribune",
    "artists": [{"name": "Martial Solal"}, {"name": "Someone Else"}],
    "id": "sp1",
    "preview_url": "https://p.scdn.co/sp1",
    "external_urls": {"spotify": "https://open.spotify.com/track/sp1"},
    "album": {
        "name": "À bout de souffle",
        "images": [{"url": "cover.jpg"}],
        "id": "al1",
    },
    "duration_ms": 123000,
}

NOT_ON_SPOTIFY = {
    "spotify_id": None,
    "preview_url": None,
    "external_urls": {},
    "album": None,
    "duration_ms": None,
}


class FakeSpotify:
    """Answers `search` from a {query: track | Exception} map."""

    def __init__(self, catalog):
        self.catalog = catalog
        self.queries = []
        self.credentials = None

    def search(self, q, type, limit):
        self.queries.append((q, type, limit))
        found = self.catalog.get(q)
        if isinstance(found, Exception):
            raise found
        return {"tracks": {"items": [found] if found else []}}


@pytest.fixture
def soundtracks(mongo):
    return mongo["movie_soundtracks"]


@pytest.fixture
def spotify(monkeypatch):
    def install(catalog=None):
        fake = FakeSpotify(catalog or {})

        def credentials(**kwargs):
            fake.credentials = kwargs
            return "credentials-manager"

        def client(client_credentials_manager):
            assert client_credentials_manager == "credentials-manager"
            return fake

        monkeypatch.setattr(controller, "SpotifyClientCredentials", credentials)
        monkeypatch.setattr(controller.spotipy, "Spotify", client)
        return fake

    return install


@pytest.fixture
def gpt(monkeypatch, fake_openai):
    def install(**kwargs):
        fake = fake_openai(**kwargs)
        monkeypatch.setattr(controller, "OpenAI", fake)
        return fake

    return install


def test_stored_soundtrack_is_returned_without_external_calls(soundtracks):
    soundtracks.insert_one(
        {"cache_key": "Breathless_1960", "description": "Jazz.", "tracks": []}
    )

    body, status = controller.get_movie_soundtrack("Breathless", 1960)

    assert status == 200
    assert body["description"] == "Jazz."
    assert isinstance(body["_id"], str)


def test_cache_key_is_only_the_title_when_there_is_no_year(soundtracks):
    soundtracks.insert_one({"cache_key": "Breathless", "description": "No year."})
    soundtracks.insert_one({"cache_key": "Breathless_1960", "description": "1960."})

    assert controller.get_movie_soundtrack("Breathless")[0]["description"] == "No year."
    assert (
        controller.get_movie_soundtrack("Breathless", 1960)[0]["description"] == "1960."
    )


def test_stored_description_is_translated_on_the_fly(soundtracks, gpt):
    soundtracks.insert_one({"cache_key": "Breathless", "description": "Jazz francês."})
    openai = gpt(reply=" French jazz. ")

    body, status = controller.get_movie_soundtrack("Breathless", language="en")

    assert status == 200
    assert body["description"] == "French jazz."
    assert openai.prompts == [
        "Translate the following soundtrack description to en: Jazz francês."
    ]
    assert soundtracks.find_one({})["description"] == "Jazz francês."


def test_translation_failure_keeps_the_stored_description(soundtracks, gpt):
    soundtracks.insert_one({"cache_key": "Breathless", "description": "Jazz francês."})
    gpt(error=TimeoutError())

    body, status = controller.get_movie_soundtrack("Breathless", language="en")

    assert status == 200
    assert body["description"] == "Jazz francês."


def test_new_soundtrack_is_built_from_gpt_and_spotify_and_saved(
    soundtracks, gpt, spotify
):
    openai = gpt(reply=f"Sure! Here it is:\n{json.dumps(GPT_TRACKS)}\nEnjoy.")
    fake_spotify = spotify(
        {"track:New York Herald Tribune artist:Martial Solal": SPOTIFY_TRACK}
    )

    body, status = controller.get_movie_soundtrack(
        "Breathless", 1960, "Jean-Luc Godard"
    )

    assert status == 200
    assert body["movie_title"] == "Breathless"
    assert body["movie_year"] == 1960
    assert body["movie_director"] == "Jean-Luc Godard"
    assert body["description"] == "Jazz francês."
    assert body["source"] == "gpt_spotify"
    assert body["cache_key"] == "Breathless_1960"
    assert body["tracks"] == [
        {
            "title": "New York Herald Tribune",
            "artist": "Martial Solal",
            "spotify_id": "sp1",
            "preview_url": "https://p.scdn.co/sp1",
            "external_urls": {"spotify": "https://open.spotify.com/track/sp1"},
            "album": {"name": "À bout de souffle", "images": [{"url": "cover.jpg"}]},
            "duration_ms": 123000,
            "description": "Tema",
        },
        {
            "title": "L'amour, la mort",
            "artist": "Martial Solal",
            "description": "",
            **NOT_ON_SPOTIFY,
        },
    ]
    assert isinstance(body["_id"], str)
    assert soundtracks.find_one({"cache_key": "Breathless_1960"})["source"] == (
        "gpt_spotify"
    )
    assert "Filme: Breathless (1960) - Diretor: Jean-Luc Godard" in openai.prompts[0]
    assert fake_spotify.queries[0] == (
        "track:New York Herald Tribune artist:Martial Solal",
        "track",
        1,
    )
    assert fake_spotify.credentials == {
        "client_id": "fake-spotify-id",
        "client_secret": "fake-spotify-secret",
    }


def test_second_request_is_served_from_the_database(soundtracks, gpt, spotify):
    openai = gpt(reply=json.dumps(GPT_TRACKS))
    spotify()

    controller.get_movie_soundtrack("Breathless", 1960)
    body, status = controller.get_movie_soundtrack("Breathless", 1960)

    assert status == 200
    assert len(openai.requests) == 1
    assert soundtracks.count_documents({}) == 1


def test_english_request_uses_the_english_prompt(soundtracks, gpt, spotify):
    openai = gpt(reply=json.dumps(GPT_TRACKS))
    spotify()

    controller.get_movie_soundtrack("Breathless", language="en")

    assert "Identify the main songs" in openai.prompts[0]
    assert openai.requests[0]["messages"][0]["content"].startswith("You are")


def test_spotify_search_failure_keeps_the_track_without_spotify_data(
    soundtracks, gpt, spotify
):
    gpt(reply=json.dumps(GPT_TRACKS))
    spotify(
        {
            "track:New York Herald Tribune artist:Martial Solal": RuntimeError("429"),
            "track:L'amour, la mort artist:Martial Solal": SPOTIFY_TRACK,
        }
    )

    body, status = controller.get_movie_soundtrack("Breathless")

    assert status == 200
    assert body["tracks"][0] == {
        "title": "New York Herald Tribune",
        "artist": "Martial Solal",
        "description": "Tema",
        **NOT_ON_SPOTIFY,
    }
    assert body["tracks"][1]["spotify_id"] == "sp1"


@pytest.mark.parametrize("missing", ["SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"])
def test_without_spotify_credentials_the_soundtrack_is_answered_but_not_saved(
    soundtracks, gpt, monkeypatch, missing
):
    gpt(reply=json.dumps(GPT_TRACKS))
    monkeypatch.setattr(controller, missing, None)

    body, status = controller.get_movie_soundtrack("Breathless")

    assert status == 200
    assert body["source"] == "gpt"
    assert body["description"] == "Jazz francês."
    assert body["tracks"][0] == {
        "title": "New York Herald Tribune",
        "artist": "Martial Solal",
        "description": "Tema",
        **NOT_ON_SPOTIFY,
    }
    assert len(body["tracks"]) == 2
    assert "_id" not in body
    assert soundtracks.count_documents({}) == 0


def test_spotify_client_failure_is_not_saved_either(soundtracks, gpt, monkeypatch):
    gpt(reply=json.dumps(GPT_TRACKS))

    def refuse(**kwargs):
        raise RuntimeError("invalid client")

    monkeypatch.setattr(controller, "SpotifyClientCredentials", refuse)

    body, status = controller.get_movie_soundtrack("Breathless")

    assert status == 200
    assert body["source"] == "gpt"
    assert [t["title"] for t in body["tracks"]] == [
        "New York Herald Tribune",
        "L'amour, la mort",
    ]
    assert soundtracks.count_documents({}) == 0


def test_every_spotify_search_failing_is_not_saved_either(soundtracks, gpt, spotify):
    """spotipy authenticates lazily, so a bad credential fails on each search."""
    gpt(reply=json.dumps(GPT_TRACKS))
    spotify(
        {
            "track:New York Herald Tribune artist:Martial Solal": RuntimeError("401"),
            "track:L'amour, la mort artist:Martial Solal": RuntimeError("401"),
        }
    )

    body, status = controller.get_movie_soundtrack("Breathless")

    assert status == 200
    assert body["source"] == "gpt"
    assert len(body["tracks"]) == 2
    assert soundtracks.count_documents({}) == 0


def test_soundtrack_is_saved_once_spotify_is_back(
    soundtracks, gpt, spotify, monkeypatch
):
    gpt(reply=json.dumps(GPT_TRACKS))
    monkeypatch.setattr(controller, "SPOTIFY_CLIENT_ID", None)
    controller.get_movie_soundtrack("Breathless")
    monkeypatch.setattr(controller, "SPOTIFY_CLIENT_ID", "fake-spotify-id")
    spotify({"track:New York Herald Tribune artist:Martial Solal": SPOTIFY_TRACK})

    body, status = controller.get_movie_soundtrack("Breathless")

    assert status == 200
    assert body["source"] == "gpt_spotify"
    assert body["tracks"][0]["spotify_id"] == "sp1"
    assert soundtracks.count_documents({"cache_key": "Breathless"}) == 1


def test_track_without_title_is_the_only_one_discarded(soundtracks, gpt, spotify):
    reply = {
        "tracks": [
            {"artist": "Nobody"},
            GPT_TRACKS["tracks"][0],
            "not a track",
            {"title": "Duo"},
        ]
    }
    gpt(reply=json.dumps(reply))
    fake_spotify = spotify(
        {"track:New York Herald Tribune artist:Martial Solal": SPOTIFY_TRACK}
    )

    body, status = controller.get_movie_soundtrack("Breathless")

    assert status == 200
    assert [(t["title"], t["artist"]) for t in body["tracks"]] == [
        ("New York Herald Tribune", "Martial Solal"),
        ("Duo", ""),
    ]
    # A track without artist is searched by title only.
    assert fake_spotify.queries[1][0] == "track:Duo"
    assert soundtracks.count_documents({}) == 1


def test_track_without_title_is_also_dropped_when_spotify_is_unavailable(
    soundtracks, gpt, monkeypatch
):
    gpt(reply=json.dumps({"tracks": [{"artist": "Nobody"}, {"title": "Duo"}]}))
    monkeypatch.setattr(controller, "SPOTIFY_CLIENT_SECRET", None)

    body, _ = controller.get_movie_soundtrack("Breathless")

    assert [t["title"] for t in body["tracks"]] == ["Duo"]


def test_plain_text_gpt_answer_is_parsed_line_by_line(soundtracks, gpt, spotify):
    gpt(
        reply=(
            "A trilha é marcada pelo jazz.\n"
            "1. New York Herald Tribune - Martial Solal\n"
            "2. Duo - Martial Solal - tema de amor\n"
            "3. Sem artista\n"
        )
    )
    spotify()

    body, status = controller.get_movie_soundtrack("Breathless")

    assert status == 200
    assert body["description"] == "A trilha é marcada pelo jazz."
    assert [(t["title"], t["artist"]) for t in body["tracks"]] == [
        ("New York Herald Tribune", "Martial Solal"),
        ("Duo", "Martial Solal"),
    ]


def test_manual_parser_accepts_any_item_number():
    content = "Trilha marcante.\n" + "\n".join(
        f"{n}. Song {n} - Artist {n}" for n in range(1, 8)
    )

    parsed = controller._parse_gpt_response_manually(content)

    assert [t["title"] for t in parsed["tracks"]] == [f"Song {n}" for n in range(1, 8)]
    assert parsed["tracks"][6]["artist"] == "Artist 7"
    assert parsed["description"] == "Trilha marcante."


def test_manual_parser_reads_two_digit_and_parenthesis_numbering():
    parsed = controller._parse_gpt_response_manually(
        "10. Tenth - Someone\n11) Eleventh - Someone Else\n2001: A Space Odyssey"
    )

    assert [(t["title"], t["artist"]) for t in parsed["tracks"]] == [
        ("Tenth", "Someone"),
        ("Eleventh", "Someone Else"),
    ]
    assert parsed["description"] == "2001: A Space Odyssey"


def test_manual_parser_keeps_at_most_eight_tracks():
    content = "\n".join(f"{n}. Song {n} - Artist {n}" for n in range(1, 13))

    assert len(controller._parse_gpt_response_manually(content)["tracks"]) == 8


def test_manual_parser_returns_none_for_non_text():
    assert controller._parse_gpt_response_manually(None) is None


def test_invalid_json_in_the_gpt_answer_falls_back_to_the_manual_parser(
    soundtracks, gpt, spotify
):
    gpt(reply='{"tracks": [oops]}\n1. Duo - Martial Solal')
    spotify()

    body, status = controller.get_movie_soundtrack("Breathless")

    assert status == 200
    assert [t["title"] for t in body["tracks"]] == ["Duo"]


@pytest.mark.parametrize(
    "language, message",
    [
        ("pt", "Não foi possível encontrar a trilha sonora do filme"),
        ("en", "Could not find movie soundtrack"),
    ],
)
def test_openai_failure_is_404_and_nothing_is_cached(
    soundtracks, gpt, language, message
):
    gpt(error=RuntimeError("503"))

    body, status = controller.get_movie_soundtrack("Breathless", language=language)

    assert status == 404
    assert body == {"error": message}
    assert soundtracks.count_documents({}) == 0


@pytest.mark.parametrize(
    "reply", ['{"tracks": [], "description": "Nothing"}', "I do not know this movie."]
)
def test_gpt_answer_without_tracks_is_404(soundtracks, gpt, reply):
    gpt(reply=reply)

    assert controller.get_movie_soundtrack("Breathless")[1] == 404
    assert soundtracks.count_documents({}) == 0


def test_without_an_openai_key_a_new_soundtrack_is_404(soundtracks, monkeypatch):
    monkeypatch.setattr(controller, "OPENAI_API_KEY", None)

    assert controller.get_movie_soundtrack("Breathless")[1] == 404


@pytest.mark.parametrize(
    "language, message",
    [("pt", "Erro ao buscar trilha sonora"), ("en", "Error searching soundtrack")],
)
def test_database_down_is_500(database_down, language, message):
    body, status = controller.get_movie_soundtrack("Breathless", language=language)

    assert status == 500
    assert body == {"error": message}


def test_get_all_soundtracks_hides_the_ids(soundtracks):
    soundtracks.insert_one({"cache_key": "Breathless", "tracks": []})

    body, status = controller.get_all_soundtracks()

    assert status == 200
    assert body == {"soundtracks": [{"cache_key": "Breathless", "tracks": []}]}


def test_get_all_soundtracks_with_the_database_down_is_500(database_down):
    assert controller.get_all_soundtracks()[1] == 500


def test_delete_soundtrack_uses_the_same_cache_key(soundtracks):
    soundtracks.insert_one({"cache_key": "Breathless"})
    soundtracks.insert_one({"cache_key": "Breathless_1960"})

    body, status = controller.delete_soundtrack("Breathless", 1960)

    assert status == 200
    assert body == {"message": "Trilha sonora de Breathless removida com sucesso"}
    assert [s["cache_key"] for s in soundtracks.find()] == ["Breathless"]


def test_delete_unknown_soundtrack_is_404(soundtracks):
    soundtracks.insert_one({"cache_key": "Breathless_1960"})

    body, status = controller.delete_soundtrack("Breathless")

    assert status == 404
    assert soundtracks.count_documents({}) == 1


def test_delete_soundtrack_with_the_database_down_is_500(database_down):
    assert controller.delete_soundtrack("Breathless")[1] == 500
