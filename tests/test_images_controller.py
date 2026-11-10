from datetime import datetime

import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from images import controller


class FakeS3:
    def __init__(self, objects=None, tags=None, error=None):
        self.objects = objects or []
        self.tags = tags or {}
        self.error = error
        self.calls = []

    def list_objects_v2(self, **kwargs):
        self.calls.append(("list_objects_v2", kwargs))
        if self.error:
            raise self.error
        return {"Contents": self.objects} if self.objects else {}

    def get_object_tagging(self, **kwargs):
        self.calls.append(("get_object_tagging", kwargs))
        if self.error:
            raise self.error
        tags = self.tags.get(kwargs["Key"], {})
        return {"TagSet": [{"Key": k, "Value": v} for k, v in tags.items()]}


@pytest.fixture
def s3(monkeypatch):
    def install(**kwargs):
        fake = FakeS3(**kwargs)
        monkeypatch.setattr(controller.boto3, "client", lambda *a, **kw: fake)
        return fake

    return install


NO_SUCH_KEY = ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObjectTagging")


def test_all_images_are_listed_oldest_first_with_their_subtitles(s3):
    fake = s3(
        objects=[
            {"Key": "tt1/second.jpg", "LastModified": datetime(2024, 2, 1)},
            {"Key": "tt1/first.jpg", "LastModified": datetime(2024, 1, 1)},
        ],
        tags={
            "tt1/first.jpg": {
                "subtitle_pt": "Cena final",
                "subtitle_en": "Final scene",
                "author": "ignored",
            },
            "tt1/second.jpg": {"subtitle_pt": "Bastidores"},
        },
    )

    body, status = controller.get_all_image_urls("test-bucket", "tt1")

    assert status == 200
    assert body == {
        "images": [
            {
                "url": "https://test-bucket.s3.us-east-2.amazonaws.com/tt1/first.jpg",
                "filename": "first.jpg",
                "subtitle_pt": "Cena final",
                "subtitle_en": "Final scene",
            },
            {
                "url": "https://test-bucket.s3.us-east-2.amazonaws.com/tt1/second.jpg",
                "filename": "second.jpg",
                "subtitle_pt": "Bastidores",
                "subtitle_en": "",
            },
        ]
    }
    assert fake.calls[0] == (
        "list_objects_v2",
        {"Bucket": "test-bucket", "Prefix": "tt1/"},
    )


def test_movie_without_images_is_200_with_an_empty_list(s3):
    s3()

    assert controller.get_all_image_urls("test-bucket", "tt1") == ({"images": []}, 200)


def test_urls_use_the_configured_bucket_not_the_one_passed_in(s3):
    """Current behaviour: the argument lists the objects, config builds the URL."""
    fake = s3(objects=[{"Key": "tt1/a.jpg", "LastModified": datetime(2024, 1, 1)}])

    body, _ = controller.get_all_image_urls("another-bucket", "tt1")

    assert fake.calls[0][1]["Bucket"] == "another-bucket"
    assert body["images"][0]["url"].startswith("https://test-bucket.s3.")


def test_listing_failure_from_s3_is_500(s3):
    s3(error=ClientError({"Error": {"Code": "AccessDenied"}}, "ListObjectsV2"))

    body, status = controller.get_all_image_urls("test-bucket", "tt1")

    assert status == 500
    assert body == {"status": 500, "message": "Erro ao listar imagens"}


def test_listing_only_handles_client_errors(s3):
    """Current behaviour: anything but ClientError escapes the controller."""
    s3(error=NoCredentialsError())

    with pytest.raises(NoCredentialsError):
        controller.get_all_image_urls("test-bucket", "tt1")


def test_single_image_returns_url_and_subtitles(s3):
    fake = s3(tags={"tt1/a.jpg": {"subtitle_pt": "Legenda", "subtitle_en": "Caption"}})

    body, status = controller.get_image_url("test-bucket", "tt1", "a.jpg")

    assert status == 200
    assert body == {
        "url": "https://test-bucket.s3.us-east-2.amazonaws.com/tt1/a.jpg",
        "filename": "a.jpg",
        "subtitle_pt": "Legenda",
        "subtitle_en": "Caption",
    }
    assert fake.calls == [
        ("get_object_tagging", {"Bucket": "test-bucket", "Key": "tt1/a.jpg"})
    ]


def test_single_image_without_tags_has_empty_subtitles(s3):
    s3()

    body, status = controller.get_image_url("test-bucket", "tt1", "a.jpg")

    assert status == 200
    assert (body["subtitle_pt"], body["subtitle_en"]) == ("", "")


@pytest.mark.parametrize("failure", [NO_SUCH_KEY, NoCredentialsError()])
def test_single_image_failure_is_500_even_for_a_missing_object(s3, failure):
    """Current behaviour: a missing key is reported as 500, never 404."""
    s3(error=failure)

    body, status = controller.get_image_url("test-bucket", "tt1", "nope.jpg")

    assert status == 500
    assert body == {"status": 500, "message": "Erro ao buscar imagem"}
