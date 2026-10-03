"""Read a dialog screenshot with an open vision model served by Ollama on this machine.

Needs Ollama running at config.READER_URL with config.READER_MODEL pulled.
"""
import base64
import json
import re
import urllib.error
import urllib.request

from backend import config

PROMPT = (
    "This is a screenshot from the game Arknights: story dialog, the story log, a choice, or a chapter menu. "
    "Reply with JSON only, no commentary: "
    '{"speaker": "<the name in the speaker box, or empty if there is none>", '
    '"text": "<all the story text on screen, exactly as written, in reading order, including the names beside lines>"}'
)
# Ollama turns this into a grammar, so the reply can only be an object with these two strings.
SCHEMA = {"type": "object", "properties": {"speaker": {"type": "string"}, "text": {"type": "string"}}, "required": ["speaker", "text"]}


def parse(reply):
    """Model reply -> {"speaker", "text"}. Code fences are stripped, and a literal backslash-n in the text (the model
    sometimes escapes line breaks twice on log views) becomes a line break, so names after it still match. A reply
    that isn't the JSON object asked for is kept whole as the text, so the names in it can still be matched."""
    try:
        data = json.loads(re.sub(r"^```\w*|```$", "", reply.strip()))
    except ValueError:
        data = None
    if not isinstance(data, dict):
        return {"speaker": "", "text": reply}
    return {"speaker": str(data.get("speaker") or ""), "text": str(data.get("text") or "").replace("\\n", "\n")}


def read(image):
    """Image bytes -> {"speaker", "text"}. Raises RuntimeError when Ollama is down, the model isn't pulled, or Ollama refuses."""
    return parse(chat(PROMPT, SCHEMA, [base64.b64encode(image).decode()]))


def chat(prompt, schema, images=()):
    """The model's reply to one prompt, held to a JSON schema. Raises RuntimeError as read() does."""
    body = {
        "model": config.READER_MODEL,
        "messages": [{"role": "user", "content": prompt, "images": list(images)}],
        "format": schema,
        "stream": False,
        "think": False,  # reading text needs no reasoning; qwen3.5:4b would think by default
        "options": {"temperature": 0},  # the same input should get the same answer every time
    }
    request = urllib.request.Request(config.READER_URL + "/api/chat", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.load(response)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError(f"Model not pulled: ollama pull {config.READER_MODEL}") from e
        raise RuntimeError(f"Ollama error {e.code}: {e.read().decode(errors='replace')}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama isn't running at {config.READER_URL}. Start it: brew services start ollama (macOS) or ollama serve.") from e
    return data["message"]["content"]
