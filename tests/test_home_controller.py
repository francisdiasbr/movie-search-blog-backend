from datetime import datetime

import pytest
from botocore.exceptions import ClientError

from home import controller


class FakeS3:
    """Answers `list_objects_v2` from a {prefix: [keys] | Exception} map."""

    def __init__(self, objects):
        self.objects = objects
        self.calls = []

    def list_objects_v2(self, **kwargs):
        self.calls.append(kwargs)
        keys = self.objects.get(kwargs["Prefix"], [])
        if isinstance(keys, Exception):
            raise keys
        if not keys:
            return {}
        return {"Contents": [{"Key": key} for key in keys]}


@pytest.fixture
def s3(monkeypatch):
    """Installs a FakeS3 behind `boto3.client` and records how it was built."""

    def install(objects):
        fake = FakeS3(objects)
        fake.created_with = []

        def client(*args, **kwargs):
            fake.created_with.append((args, kwargs))
            return fake

        monkeypatch.setattr(controller.boto3, "client", client)
        return fake

    return install


@pytest.fixture
def reviews(mongo):
    collection = mongo["authoralreviewslist"]
    collection.insert_many(
        [
            {
                "tconst": "tt1",
                "primaryTitle": "Breathless",
                "created_at": "2024-01-01",
                "content": {"pt": {"text": "long text"}},
                "isAiGenerated": False,
            },
            {
                "tconst": "tt2",
                "primaryTitle": "Contempt",
                "created_at": "2024-02-01",
                "content": {"pt": {"text": "long text"}},
                "isAiGenerated": True,
            },
        ]
    )
    return collection


def test_cards_carry_the_first_s3_image_of_each_review(reviews, s3):
    fake = s3({"tt1/": ["tt1/a.jpg", "tt1/b.jpg"], "tt2/": ["tt2/poster.png"]})

    body, status = controller.get_home_cards()

    assert status == 200
    assert body["total_documents"] == 2
    assert [
        (e["tconst"], e["primaryTitle"], e["created_at"], e["imageUrl"])
        for e in body["entries"]
    ] == [
        (
            "tt2",
            "Contempt",
            "2024-02-01",
            "https://test-bucket.s3.us-east-2.amazonaws.com/tt2/poster.png",
        ),
        (
            "tt1",
            "Breathless",
            "2024-01-01",
            "https://test-bucket.s3.us-east-2.amazonaws.com/tt1/a.jpg",
        ),
    ]
    assert {"Bucket": "test-bucket", "Prefix": "tt1/", "MaxKeys": 1} in fake.calls


def test_cards_only_expose_the_card_fields(reviews, s3):
    s3({})

    body, _ = controller.get_home_cards()

    assert set(body["entries"][0]) == {
        "_id",
        "tconst",
        "primaryTitle",
        "created_at",
        "imageUrl",
    }
    assert isinstance(body["entries"][0]["_id"], str)


def test_review_without_images_gets_a_null_image(reviews, s3):
    s3({"tt1/": ["tt1/a.jpg"]})

    body, status = controller.get_home_cards()

    assert status == 200
    assert {e["tconst"]: e["imageUrl"] for e in body["entries"]}["tt2"] is None


@pytest.mark.parametrize(
    "failure",
    [
        ClientError({"Error": {"Code": "AccessDenied"}}, "ListObjectsV2"),
        RuntimeError("connection reset"),
    ],
)
def test_s3_failure_for_one_review_does_not_break_the_others(reviews, s3, failure):
    s3({"tt1/": failure, "tt2/": ["tt2/poster.png"]})

    body, status = controller.get_home_cards()
    images = {e["tconst"]: e["imageUrl"] for e in body["entries"]}

    assert status == 200
    assert images["tt1"] is None
    assert images["tt2"].endswith("/tt2/poster.png")


def test_missing_title_and_date_default_to_empty_strings(mongo, s3):
    mongo["authoralreviewslist"].insert_one({"tconst": "tt7"})
    s3({})

    body, _ = controller.get_home_cards()

    assert body["entries"][0]["primaryTitle"] == ""
    assert body["entries"][0]["created_at"] == ""


def test_title_and_tconst_filters_are_case_insensitive_substrings(reviews, s3):
    s3({})

    by_title, _ = controller.get_home_cards(filters={"primaryTitle": "breath"})
    by_tconst, _ = controller.get_home_cards(filters={"tconst": "TT2"})

    assert [e["tconst"] for e in by_title["entries"]] == ["tt1"]
    assert [e["tconst"] for e in by_tconst["entries"]] == ["tt2"]
    assert by_title["total_documents"] == 1


def test_other_filters_match_exactly(reviews, s3):
    s3({})

    body, _ = controller.get_home_cards(filters={"isAiGenerated": True})

    assert [e["tconst"] for e in body["entries"]] == ["tt2"]


def test_cards_paginate_but_report_the_full_total(reviews, s3):
    s3({})

    body, status = controller.get_home_cards(page=2, page_size=1)

    assert status == 200
    assert [e["tconst"] for e in body["entries"]] == ["tt1"]
    assert body["total_documents"] == 2


def test_s3_client_is_built_once_with_the_configured_credentials(reviews, s3):
    fake = s3({})

    controller.get_home_cards(page_size=1)
    controller.get_home_cards(page_size=1)

    assert fake.created_with == [
        (
            ("s3",),
            {
                "aws_access_key_id": "fake-aws-key-id",
                "aws_secret_access_key": "fake-aws-secret",
                "region_name": "us-east-2",
            },
        )
    ]
    assert len(fake.calls) == 2


def test_no_matching_review_is_a_500(reviews, s3):
    """Current behaviour: ThreadPoolExecutor(max_workers=0) raises ValueError."""
    s3({})

    empty_filter = controller.get_home_cards(filters={"tconst": "tt9"})
    past_the_end = controller.get_home_cards(page=3)

    assert empty_filter == ({"status": 500, "message": "Erro ao buscar cards"}, 500)
    assert past_the_end[1] == 500


def test_review_without_tconst_is_a_500(reviews, s3):
    """Current behaviour: one malformed document breaks the whole page."""
    reviews.insert_one({"primaryTitle": "Untitled", "created_at": datetime.now()})
    s3({})

    assert controller.get_home_cards()[1] == 500


def test_database_down_is_500(database_down):
    body, status = controller.get_home_cards()

    assert status == 500
    assert body == {"status": 500, "message": "Banco de dados indisponível"}
