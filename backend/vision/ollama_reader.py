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
    "This is a screenshot of story dialog from the game Arknights. Reply with JSON only, no commentary: "
    '{"speaker": "<the name in the speaker box, or empty if there is none>", "text": "<the dialog text, exactly as written>"}'
)
# Ollama turns this into a grammar, so the reply can only be an object with these two strings.
SCHEMA = {"type": "object", "properties": {"speaker": {"type": "string"}, "text": {"type": "string"}}, "required": ["speaker", "text"]}


def parse(reply):
    """Model reply -> {"speaker", "text"}. Code fences are stripped. A reply that isn't the JSON object
    asked for is kept whole as the text, so the names in it can still be matched."""
    try:
        data = json.loads(re.sub(r"^```\w*|```$", "", reply.strip()))
    except ValueError:
        data = None
    if not isinstance(data, dict):
        return {"speaker": "", "text": reply}
    return {"speaker": str(data.get("speaker") or ""), "text": str(data.get("text") or "")}


def read(image):
    """Image bytes -> {"speaker", "text"}. Raises RuntimeError when Ollama is down, the model isn't pulled, or Ollama refuses."""
    body = {
        "model": config.READER_MODEL,
        "messages": [{"role": "user", "content": PROMPT, "images": [base64.b64encode(image).decode()]}],
        "format": SCHEMA,
        "stream": False,
        "think": False,  # reading text needs no reasoning; qwen3.5:4b would think by default
        "options": {"temperature": 0},  # the same screenshot should read the same way every time
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
    return parse(data["message"]["content"])
