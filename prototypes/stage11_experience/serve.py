"""PROTOTYPE — serve the Stage 11 experience study with one command."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import webbrowser


ROOT = Path(__file__).parent
PORT = 8111


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)


if __name__ == "__main__":
    url = f"http://127.0.0.1:{PORT}/?variant=A&surface=maker"
    print(f"Stage 11 prototype: {url}")
    webbrowser.open(url)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
