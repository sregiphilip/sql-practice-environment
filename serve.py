"""Serve the Exercise 2 workbook locally and auto-save answers to disk.

The page POSTs to /save after every change; this writes:
  my_answers.md    readable copy of your queries, check results and result previews
  my_answers.json  full workbook state (the page merges it with browser storage on load)

Safety nets so answers are never lost:
  - before each save, the previous my_answers.json is copied into history/ (at most once a minute while typing,
    immediately when a status changes; last 300 kept)
  - a save that would replace written SQL with an empty workbook is refused
  - /backup stores a browser's copy in history/ before the page merges it with the file

Usage: python3 serve.py [port]   (default 8765, localhost only)
"""
import json
import sys
import time
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
MD = ROOT / "my_answers.md"
STATE = ROOT / "my_answers.json"
HISTORY = ROOT / "history"
KEEP = 300
SNAPSHOT_EVERY = 60  # seconds between history copies while you're typing
_last_snapshot = 0.0
STATUS = {"todo": "Not started", "draft": "In progress", "done": "Verified"}


def render_md(doc):
    out = [f"# Exercise 2 · SQL answers\n\n_Last saved {doc['updated']}_\n"]
    group = None
    for it in doc["items"]:
        if it["group"] != group:
            group = it["group"]
            out.append(f"\n## {group}\n")
        out.append(f"\n### {it['short']}. {it['question']}\n")
        line = f"**Status:** {STATUS.get(it['status'], it['status'])}"
        if it.get("check"):
            line += f" · **Self-check:** {it['check']}"
        out.append(line + "\n")
        out.append(f"```sql\n{it['sql'] or '-- no query yet'}\n```\n")
        if it.get("error"):
            out.append(f"Last run returned an error:\n\n```\n{it['error']}\n```\n")
        elif it.get("result") and it["result"]["columns"]:
            r = it["result"]
            esc = lambda v: str(v).replace("|", "\\|")
            out.append("| " + " | ".join(map(esc, r["columns"])) + " |")
            out.append("|" + "|".join("---" for _ in r["columns"]) + "|")
            out += ["| " + " | ".join(map(esc, row)) + " |" for row in r["rows"]]
            if r["rowCount"] > len(r["rows"]):
                out.append(f"\n_{r['rowCount']} rows in total; first {len(r['rows'])} shown._")
            out.append("")
    return "\n".join(out) + "\n"


def fingerprint(state):
    """What matters for history: each question's SQL and status (not cached result rows)."""
    return {k: ((it.get("sql") or "").strip(), it.get("status")) for k, it in (state or {}).get("items", {}).items()}


def sql_count(state):
    return sum(1 for it in (state or {}).get("items", {}).values() if (it.get("sql") or "").strip())


def snapshot(text, prefix):
    HISTORY.mkdir(exist_ok=True)
    (HISTORY / f"{prefix}-{datetime.now():%Y%m%d-%H%M%S-%f}.json").write_text(text)
    old = sorted(p for p in HISTORY.glob("answers-*.json"))
    for p in old[:-KEEP]:
        p.unlink()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def do_POST(self):
        if self.path not in ("/save", "/backup"):
            self.send_error(404)
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            if self.path == "/backup":
                snapshot(json.dumps(body, indent=1), "browser")
            else:
                new_text = json.dumps(body["state"], indent=1)
                if STATE.exists():
                    old_text = STATE.read_text()
                    if sql_count(body["state"]) == 0 and sql_count(json.loads(old_text)) > 0:
                        self.send_error(409, "refusing to replace saved answers with an empty workbook")
                        return
                    global _last_snapshot
                    old_fp, new_fp = fingerprint(json.loads(old_text)), fingerprint(body["state"])
                    status_changed = {k: v[1] for k, v in old_fp.items()} != {k: v[1] for k, v in new_fp.items()}
                    if old_fp != new_fp and (status_changed or time.time() - _last_snapshot >= SNAPSHOT_EVERY):
                        snapshot(old_text, "answers")
                        _last_snapshot = time.time()
                STATE.write_text(new_text)
                MD.write_text(render_md(body["doc"]))
        except Exception as e:  # keep the server alive on a bad payload
            self.send_error(400, str(e))
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")  # always serve the latest build and answers
        super().end_headers()

    def log_message(self, fmt, *args):
        if self.command == "POST":
            print(f"{datetime.now():%H:%M:%S} saved answers")
        elif not str(args[1]).startswith(("2", "3")):
            super().log_message(fmt, *args)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"Open http://localhost:{port}/")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
