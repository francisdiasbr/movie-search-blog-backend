"""Shared fixtures.

No test may reach Atlas, S3, OpenAI, Spotify, IMDB or TMDB:

* the credentials are replaced by fake values before `config` is imported
  (`load_dotenv` never overrides a variable that is already set) and again,
  per test, on every module that copied them at import time;
* Mongo is replaced by mongomock for every test;
* every real external client is replaced by a guard that records the attempt
  and raises. The controllers swallow most exceptions, so the guard fixture
  also fails the test on teardown when anything was recorded.

Each test module then mocks the external calls of the controller it covers.
"""

import os
import socket
from types import SimpleNamespace

FAKE_ENV = {
    "MONGODB_CONNECTION_STRING": "mongodb://offline.invalid:27017",
    "MONGODB_DATABASE": "test",
    "AWS_ACCESS_KEY_ID": "fake-aws-key-id",
    "AWS_SECRET_ACCESS_KEY": "fake-aws-secret",
    "BUCKET_NAME": "test-bucket",
    "OPENAI_API_KEY": "fake-openai-key",
    "SPOTIFY_CLIENT_ID": "fake-spotify-id",
    "SPOTIFY_CLIENT_SECRET": "fake-spotify-secret",
}
os.environ.update(FAKE_ENV)

import boto3  # noqa: E402
import mongomock  # noqa: E402
import openai  # noqa: E402
import pytest  # noqa: E402
import requests  # noqa: E402
import spotipy  # noqa: E402

import config  # noqa: E402
import directors.controller  # noqa: E402
import home.controller  # noqa: E402
import images.controller  # noqa: E402
import images.routes  # noqa: E402
import movie_detail_cache.controller  # noqa: E402
import music.controller  # noqa: E402

# Modules that copied a credential with `from config import ...`.
CREDENTIAL_HOLDERS = {
    "OPENAI_API_KEY": [
        config,
        directors.controller,
        movie_detail_cache.controller,
        music.controller,
    ],
    "SPOTIFY_CLIENT_ID": [config, music.controller],
    "SPOTIFY_CLIENT_SECRET": [config, music.controller],
    "AWS_ACCESS_KEY_ID": [config, home.controller, images.controller],
    "AWS_SECRET_ACCESS_KEY": [config, home.controller, images.controller],
    "BUCKET_NAME": [config, home.controller, images.controller, images.routes],
    "MONGODB_CONNECTION_STRING": [config],
}


@pytest.fixture(autouse=True)
def fake_credentials(monkeypatch):
    """Fake keys in the environment and in every module that holds a copy."""
    for name, value in FAKE_ENV.items():
        monkeypatch.setenv(name, value)
    for name, modules in CREDENTIAL_HOLDERS.items():
        for module in modules:
            monkeypatch.setattr(module, name, FAKE_ENV[name])


@pytest.fixture(autouse=True)
def mongo(monkeypatch):
    """In-memory database that `config.get_mongo_collection` hands out."""
    client = mongomock.MongoClient()
    monkeypatch.setattr(config, "get_mongo_client", lambda: client)
    monkeypatch.setattr(config, "_mongo_client", None)
    monkeypatch.setattr(config, "MONGODB_DATABASE", "test")
    return client["test"]


@pytest.fixture(autouse=True)
def no_external_calls(monkeypatch):
    """Fail any test that reaches a real external client or opens a socket."""
    attempts = []

    def forbid(name):
        def guard(*args, **kwargs):
            attempts.append(name)
            raise AssertionError(f"unmocked external call: {name}")

        return guard

    monkeypatch.setattr(directors.controller, "OpenAI", forbid("OpenAI"))
    monkeypatch.setattr(music.controller, "OpenAI", forbid("OpenAI"))
    # movie_detail_cache imports OpenAI inside its functions.
    monkeypatch.setattr(openai, "OpenAI", forbid("OpenAI"))
    monkeypatch.setattr(spotipy, "Spotify", forbid("spotipy.Spotify"))
    monkeypatch.setattr(
        music.controller,
        "SpotifyClientCredentials",
        forbid("SpotifyClientCredentials"),
    )
    monkeypatch.setattr(boto3, "client", forbid("boto3.client"))
    monkeypatch.setattr(requests, "get", forbid("requests.get"))
    monkeypatch.setattr(requests.Session, "request", forbid("requests.Session"))
    monkeypatch.setattr(socket.socket, "connect", forbid("socket.connect"))
    monkeypatch.setattr(socket.socket, "connect_ex", forbid("socket.connect_ex"))
    monkeypatch.setattr(socket, "getaddrinfo", forbid("socket.getaddrinfo"))
    # Cached S3 clients must not leak from one test to the next.
    monkeypatch.setattr(home.controller, "_s3_client", None)
    monkeypatch.setattr(images.controller, "_s3_client", None)

    yield attempts

    assert not attempts, f"unmocked external calls: {attempts}"


@pytest.fixture
def database_down(monkeypatch):
    """Mongo unreachable: `config.get_mongo_collection` returns None."""
    monkeypatch.setattr(config, "get_mongo_client", lambda: None)


class FakeOpenAI:
    """Stands in for `openai.OpenAI`; answers every chat with `reply`."""

    def __init__(self, reply=None, error=None):
        self.reply = reply
        self.error = error
        self.api_keys = []
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def __call__(self, api_key=None, **kwargs):
        self.api_keys.append(api_key)
        return self

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        if self.error:
            raise self.error
        message = SimpleNamespace(content=self.reply)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    @property
    def prompts(self):
        return [request["messages"][-1]["content"] for request in self.requests]


@pytest.fixture
def fake_openai():
    """Factory of OpenAI stand-ins: `fake_openai(reply=...)` or `(error=...)`."""
    return FakeOpenAI
