"""Offline checks for v1: keyword matching, the reader's request and reply handling, the reading cache and POST /analyze.
No network and no Ollama: the index is fake and the reader is stubbed.

    python -m tests.test_v1
"""
import io
import json
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from backend import config
from backend.app import app
from backend.index import build_index, matcher
from backend.scraper import wiki_client
from backend.vision import ollama_reader

config.DB_PATH = Path(tempfile.mkdtemp()) / "test.db"
wiki_client.all_pages = lambda: iter([
    {"title": "Rhodes Island"}, {"title": "Rhodes"}, {"title": "Island"}, {"title": "Amiya"}, {"title": "Kal'tsit"},
    {"title": "Silence"}, {"title": "Doctor"},
    {"title": "Reunion", "redirects": [{"title": "Reunion Movement"}]},
    {"title": "Guard", "categories": [{"title": "Category:Classes"}]},  # noise: a class, not lore
])
build_index.build()

real_read = ollama_reader.read
calls = []
ollama_reader.read = lambda image: calls.append(image) or {"speaker": "Amiya", "text": "Doctor, the island!"}


def test_find():
    text = "Amiya’s orders, Doctor: the Reunion Movement is headed for Rhodes Island. Kal'tsit wants silence. Guard the island!"
    # Speaker first. "silence" is lower case but the speaker already made it a keyword; "island" and Doctor need context.
    assert matcher.find("Silence", text) == {
        "keywords": ["Silence", "Amiya", "Reunion", "Rhodes Island", "Kal'tsit"],
        "needs_context": ["Doctor", "Island"],
    }
    assert matcher.find("", "RHODES ISLAND!") == {"keywords": ["Rhodes Island"], "needs_context": []}


def test_parse():
    assert ollama_reader.parse('```json\n{"speaker": "Amiya", "text": "Doctor?"}\n```') == {"speaker": "Amiya", "text": "Doctor?"}
    assert ollama_reader.parse('{"speaker": null, "text": "Hi"}') == {"speaker": "", "text": "Hi"}
    assert ollama_reader.parse("Amiya: Doctor?") == {"speaker": "", "text": "Amiya: Doctor?"}  # not JSON: kept as text
    assert ollama_reader.parse('["Amiya"]') == {"speaker": "", "text": '["Amiya"]'}


def test_read():
    """The request Ollama gets, its reply unwrapped, and the two errors a user can act on."""
    outcomes = []  # what the fake Ollama does next: reply bytes, or an exception to raise

    def fake_urlopen(request, timeout):
        body = json.loads(request.data)
        assert request.full_url == config.READER_URL + "/api/chat"
        assert body["model"] == config.READER_MODEL and body["format"] == ollama_reader.SCHEMA and body["stream"] is False
        assert body["messages"][0]["images"] == ["aGVsbG8="]  # b"hello"
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return io.BytesIO(outcome)

    saved = urllib.request.urlopen
    urllib.request.urlopen = fake_urlopen
    try:
        outcomes.append(b'{"message": {"content": "{\\"speaker\\": \\"Amiya\\", \\"text\\": \\"Hi\\"}"}}')
        assert real_read(b"hello") == {"speaker": "Amiya", "text": "Hi"}
        for error, message in [(urllib.error.URLError(ConnectionRefusedError()), "isn't running"),
                               (urllib.error.HTTPError("", 404, "Not Found", {}, io.BytesIO(b"")), "ollama pull " + config.READER_MODEL)]:
            outcomes.append(error)
            try:
                real_read(b"hello")
            except RuntimeError as e:
                assert message in str(e), e
            else:
                raise AssertionError("no error raised")
    finally:
        urllib.request.urlopen = saved


def test_analyze():
    client = app.test_client()
    post = lambda data: client.post("/analyze", data={"image": (io.BytesIO(data), "shot.png")})
    png = b"\x89PNG\r\n\x1a\n" + bytes(100)
    for _ in range(2):
        response = post(png)
        assert response.status_code == 200, response.json
        assert response.json == {"speaker": "Amiya", "text": "Doctor, the island!",
                                 "keywords": ["Amiya"], "needs_context": ["Doctor", "Island"]}
    assert calls == [png]  # the second upload of the same image was served from the cache
    assert post(b"GIF89a" + bytes(100)).status_code == 415  # named .png, but the bytes say otherwise
    app.config["MAX_CONTENT_LENGTH"] = 1000
    assert post(png * 20).status_code == 413 and "MB" in post(png * 20).json["error"]
    assert client.get("/terms?prefix=re").json == ["Reunion", "Reunion Movement"]


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("ok")
