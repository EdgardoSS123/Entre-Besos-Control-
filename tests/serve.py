from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import os
os.chdir(Path(__file__).resolve().parents[1])
class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.split('?')[0] in ['/', '/index.html']:
            self.path='/control.html'
        super().do_GET()
ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
