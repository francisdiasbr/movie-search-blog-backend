from types import SimpleNamespace

import pytest
import requests

from directors import controller

MOVIE_PAGE = """
<a href="/name/nm0000001/?ref_=tt_cl">Jean Seberg</a>
<a class="credit" href="/name/nm0000419/?ref_=tt_ov_dr">Jean-Luc Godard</a>
"""
PHOTO = "https://m.media-amazon.com/images/M/abc._V1_UX214_CR0,0,214,317_AL_.jpg"
DIRECTOR_PAGE = f"""
<img src="https://m.media-amazon.com/images/M/banner.jpg">
<img src="{PHOTO}">
"""


@pytest.fixture
def directors(mongo):
    return mongo["directors"]


@pytest.fixture
def godard(directors):
    directors.insert_one(
        {
            "name": "Jean-Luc Godard",
            "bio": "Cineasta franco-suíço.",
            "photo": "https://img/godard.jpg",
        }
    )


@pytest.fixture
def imdb(monkeypatch):
    """Serves IMDB pages from a {url: html | Exception} map."""

    def install(pages):
        requested = []

        def get(url, **kwargs):
            requested.append(url)
            page = pages.get(url, requests.HTTPError("404"))
            if isinstance(page, Exception):
                raise page
            return SimpleNamespace(text=page, raise_for_status=lambda: None)

        monkeypatch.setattr(controller.requests, "get", get)
        return requested

    return install


@pytest.fixture
def imdb_with_godard(imdb):
    return imdb(
        {
            "https://www.imdb.com/title/tt0053472/": MOVIE_PAGE,
            "https://www.imdb.com/name/nm0000419/": DIRECTOR_PAGE,
        }
    )


def test_stored_director_is_returned_without_external_calls(godard):
    body, status = controller.get_director_info("Jean-Luc Godard", "tt0053472")

    assert status == 200
    assert body["bio"] == "Cineasta franco-suíço."
    assert body["photo"] == "https://img/godard.jpg"
    assert isinstance(body["_id"], str)


def test_stored_director_without_photo_gets_one_from_imdb(directors, imdb_with_godard):
    directors.insert_one({"name": "Jean-Luc Godard", "bio": "Bio.", "photo": None})

    body, status = controller.get_director_info("Jean-Luc Godard", "tt0053472")

    assert status == 200
    assert body["photo"] == PHOTO
    assert directors.find_one({"name": "Jean-Luc Godard"})["photo"] == PHOTO
    assert imdb_with_godard == [
        "https://www.imdb.com/title/tt0053472/",
        "https://www.imdb.com/name/nm0000419/",
    ]


def test_photo_lookup_is_skipped_without_a_tconst(directors):
    directors.insert_one({"name": "Jean-Luc Godard", "bio": "Bio.", "photo": None})

    body, status = controller.get_director_info("Jean-Luc Godard")

    assert status == 200
    assert body["photo"] is None


@pytest.mark.parametrize(
    "pages",
    [
        {},
        {"https://www.imdb.com/title/tt0053472/": requests.ConnectionError("down")},
        {"https://www.imdb.com/title/tt0053472/": "<a>Somebody else</a>"},
        {
            "https://www.imdb.com/title/tt0053472/": MOVIE_PAGE,
            "https://www.imdb.com/name/nm0000419/": "<p>no pictures</p>",
        },
        {
            "https://www.imdb.com/title/tt0053472/": MOVIE_PAGE,
            "https://www.imdb.com/name/nm0000419/": ValueError("boom"),
        },
    ],
)
def test_imdb_failure_leaves_the_director_without_photo(directors, imdb, pages):
    directors.insert_one({"name": "Jean-Luc Godard", "bio": "Bio.", "photo": None})
    imdb(pages)

    body, status = controller.get_director_info("Jean-Luc Godard", "tt0053472")

    assert status == 200
    assert body["photo"] is None
    assert directors.find_one({"name": "Jean-Luc Godard"})["photo"] is None


def test_director_link_is_matched_ignoring_case(imdb_with_godard):
    assert (
        controller._get_director_id_from_movie_page("JEAN-LUC GODARD", "tt0053472")
        == "nm0000419"
    )


def test_director_page_falls_back_to_any_jpg(imdb):
    imdb(
        {
            "https://www.imdb.com/name/nm1/": (
                '<img src="https://m.media-amazon.com/images/M/only.jpg">'
            )
        }
    )

    assert (
        controller._get_director_photo_from_director_page("nm1")
        == "https://m.media-amazon.com/images/M/only.jpg"
    )


def test_stored_bio_is_translated_on_the_fly_for_english(
    godard, directors, monkeypatch, fake_openai
):
    openai = fake_openai(reply="  Franco-Swiss filmmaker.  ")
    monkeypatch.setattr(controller, "OpenAI", openai)

    body, status = controller.get_director_info("Jean-Luc Godard", language="en")

    assert status == 200
    assert body["bio"] == "Franco-Swiss filmmaker."
    assert "Cineasta franco-suíço." in openai.prompts[0]
    assert openai.api_keys == ["fake-openai-key"]
    # The translation is not cached.
    assert directors.find_one({})["bio"] == "Cineasta franco-suíço."


def test_translation_failure_keeps_the_original_bio(godard, monkeypatch, fake_openai):
    monkeypatch.setattr(controller, "OpenAI", fake_openai(error=TimeoutError()))

    body, status = controller.get_director_info("Jean-Luc Godard", language="en")

    assert status == 200
    assert body["bio"] == "Cineasta franco-suíço."


def test_translation_is_skipped_without_an_openai_key(godard, monkeypatch):
    monkeypatch.setattr(controller, "OPENAI_API_KEY", None)

    body, _ = controller.get_director_info("Jean-Luc Godard", language="en")

    assert body["bio"] == "Cineasta franco-suíço."


def test_unknown_director_gets_an_ai_bio_that_is_saved(
    directors, monkeypatch, fake_openai
):
    openai = fake_openai(reply=" Agnès Varda foi pioneira. ")
    monkeypatch.setattr(controller, "OpenAI", openai)

    body, status = controller.get_director_info("Agnès Varda")

    assert status == 200
    assert body["name"] == "Agnès Varda"
    assert body["bio"] == "Agnès Varda foi pioneira."
    assert body["photo"] is None
    assert isinstance(body["_id"], str)
    assert directors.find_one({"name": "Agnès Varda"})["bio"] == body["bio"]
    assert "português brasileiro" in openai.prompts[0]
    assert openai.requests[0]["model"] == "gpt-3.5-turbo"


def test_unknown_director_with_tconst_also_gets_the_imdb_photo(
    directors, monkeypatch, fake_openai, imdb_with_godard
):
    monkeypatch.setattr(controller, "OpenAI", fake_openai(reply="Bio."))

    body, _ = controller.get_director_info("Jean-Luc Godard", "tt0053472")

    assert body["photo"] == PHOTO
    assert directors.find_one({"name": "Jean-Luc Godard"})["photo"] == PHOTO


def test_english_request_asks_for_an_english_bio(directors, monkeypatch, fake_openai):
    openai = fake_openai(reply="Agnès Varda was a pioneer.")
    monkeypatch.setattr(controller, "OpenAI", openai)

    controller.get_director_info("Agnès Varda", language="en")

    assert "be in English" in openai.prompts[0]
    assert openai.requests[0]["messages"][0]["content"].startswith("You are")


def test_bio_generated_in_english_is_then_served_to_portuguese_requests(
    directors, monkeypatch, fake_openai
):
    """Current behaviour: the stored bio has no language, first request wins."""
    monkeypatch.setattr(controller, "OpenAI", fake_openai(reply="English bio."))
    controller.get_director_info("Agnès Varda", language="en")

    body, _ = controller.get_director_info("Agnès Varda", language="pt")

    assert body["bio"] == "English bio."


@pytest.mark.parametrize(
    "language, start",
    [("pt", "Diretor de cinema conhecido por"), ("en", "Film director known for")],
)
def test_openai_failure_stores_a_generic_fallback_bio(
    directors, monkeypatch, fake_openai, language, start
):
    """Current behaviour: the fallback text is persisted like a real bio."""
    monkeypatch.setattr(controller, "OpenAI", fake_openai(error=RuntimeError("503")))

    body, status = controller.get_director_info("Agnès Varda", language=language)

    assert status == 200
    assert body["bio"].startswith(f"{start} Agnès Varda.")
    assert directors.find_one({"name": "Agnès Varda"})["bio"] == body["bio"]


def test_without_an_openai_key_the_bio_is_a_short_placeholder(directors, monkeypatch):
    monkeypatch.setattr(controller, "OPENAI_API_KEY", "")

    pt, _ = controller.get_director_info("Agnès Varda")
    en, _ = controller.get_director_info("Chantal Akerman", language="en")

    assert pt["bio"] == "Diretor de cinema conhecido por Agnès Varda."
    assert en["bio"] == "Film director known for Chantal Akerman."


def test_tmdb_lookup_is_disabled_by_the_placeholder_key():
    """Current behaviour: the TMDB key is a hard-coded placeholder, no request."""
    assert controller._fetch_director_from_tmdb("Jean-Luc Godard") is None


def test_tmdb_result_is_saved_and_completed_with_the_imdb_photo(
    directors, monkeypatch, imdb_with_godard
):
    monkeypatch.setattr(
        controller,
        "_fetch_director_from_tmdb",
        lambda name, language: {"name": name, "bio": "TMDB bio.", "photo": None},
    )

    body, status = controller.get_director_info("Jean-Luc Godard", "tt0053472")

    assert status == 200
    assert body["bio"] == "TMDB bio."
    assert body["photo"] == PHOTO
    assert isinstance(body["_id"], str)
    assert directors.find_one({"name": "Jean-Luc Godard"})["photo"] == PHOTO


def test_comma_separated_names_are_combined(godard, directors, monkeypatch):
    monkeypatch.setattr(controller, "OPENAI_API_KEY", None)

    body, status = controller.get_director_info("Jean-Luc Godard, , Agnès Varda")

    assert status == 200
    assert body["name"] == "Jean-Luc Godard, , Agnès Varda"
    assert body["photo"] == "https://img/godard.jpg"
    assert [d["name"] for d in body["directors"]] == ["Jean-Luc Godard", "Agnès Varda"]
    assert body["bio"] == (
        "Jean-Luc Godard: Cineasta franco-suíço.\n\n"
        "Agnès Varda: Diretor de cinema conhecido por Agnès Varda."
    )
    # Each director is stored on their own; the combination is not.
    assert sorted(d["name"] for d in directors.find()) == [
        "Agnès Varda",
        "Jean-Luc Godard",
    ]


def test_only_commas_is_404(directors):
    body, status = controller.get_director_info(" , ")

    assert status == 404
    assert body == {"error": "Nenhum diretor encontrado"}


def test_database_down_is_500_for_a_single_director(database_down):
    body, status = controller.get_director_info("Jean-Luc Godard")

    assert status == 500
    assert body == {"error": "Erro ao buscar informações do diretor"}


@pytest.mark.parametrize(
    "language, bio",
    [
        ("pt", "Diretor de cinema conhecido por Joel Coen."),
        ("en", "Film director known for Joel Coen."),
    ],
)
def test_database_down_is_masked_as_200_for_several_directors(
    database_down, language, bio
):
    """Current behaviour: each failed lookup becomes a placeholder director."""
    body, status = controller.get_director_info("Joel Coen, Ethan Coen", None, language)

    assert status == 200
    assert body["directors"][0] == {"name": "Joel Coen", "bio": bio, "photo": None}
    assert body["photo"] is None


def test_missing_name_is_500(directors):
    assert controller.get_director_info(None)[1] == 500


def test_combined_bio_falls_back_to_the_names_when_joining_fails():
    directors_info = [{"name": "Joel Coen"}, {"name": "Ethan Coen"}]

    class Broken(list):
        def __iter__(self):
            if not getattr(self, "second_pass", False):
                self.second_pass = True
                raise TypeError("boom")
            return super().__iter__()

    pt = controller._create_combined_directors_bio(Broken(directors_info), "pt")
    en = controller._create_combined_directors_bio(Broken(directors_info), "en")

    assert pt == "Diretores de cinema: Joel Coen, Ethan Coen."
    assert en == "Film directors: Joel Coen, Ethan Coen."


def test_get_all_directors_hides_the_ids(godard):
    body, status = controller.get_all_directors()

    assert status == 200
    assert body == {
        "directors": [
            {
                "name": "Jean-Luc Godard",
                "bio": "Cineasta franco-suíço.",
                "photo": "https://img/godard.jpg",
            }
        ]
    }


def test_get_all_directors_with_the_database_down_is_500(database_down):
    assert controller.get_all_directors() == (
        {"error": "Erro ao buscar diretores"},
        500,
    )


def test_delete_director_removes_it(godard, directors):
    body, status = controller.delete_director("Jean-Luc Godard")

    assert status == 200
    assert "removido com sucesso" in body["message"]
    assert directors.count_documents({}) == 0


def test_delete_unknown_director_is_404(godard, directors):
    body, status = controller.delete_director("Agnès Varda")

    assert status == 404
    assert body == {"message": "Diretor Agnès Varda não encontrado"}
    assert directors.count_documents({}) == 1


def test_delete_director_with_the_database_down_is_500(database_down):
    assert controller.delete_director("x") == (
        {"error": "Erro ao deletar diretor"},
        500,
    )
