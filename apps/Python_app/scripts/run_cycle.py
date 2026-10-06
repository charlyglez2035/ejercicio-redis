"""Run and record the required POST -> GET -> PATCH -> GET -> DELETE -> GET cycle."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ISBN = f"978{int(time.time()) % 10_000_000_000:010d}"
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evidencias"


def request(base_url: str, method: str, path: str, payload=None, timeout=4):
    body = json.dumps(payload).encode() if payload is not None else None
    request_data = Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urlopen(request_data, timeout=timeout) as response:
            raw = response.read().decode()
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw
            return {"status": response.status, "body": parsed}
    except HTTPError as error:
        raw = error.read().decode()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw
        return {"status": error.code, "body": parsed}
    except (URLError, TimeoutError, OSError) as error:
        return {"status": None, "error": str(error)}


def run_cycle(name: str, base_url: str):
    payload = {
        "isbn": ISBN,
        "title": "Evidencia de ciclo API",
        "publication_year": 2026,
        "price": 125.50,
        "stock": 3,
        "format_id": 1,
        "category_id": 1,
        "authors": ["Autor de Prueba"],
    }
    updated = {"title": "Evidencia de ciclo API actualizada", "price": 140.75}
    steps = {
        "health": request(base_url, "GET", "/api/health?format=json"),
        "POST": request(base_url, "POST", "/books?format=json", payload),
        "GET_after_POST": request(base_url, "GET", f"/books/{ISBN}?format=json"),
        "PATCH": request(base_url, "PATCH", f"/books/{ISBN}?format=json", updated),
        "GET_after_PATCH": request(base_url, "GET", f"/books/{ISBN}?format=json"),
        "DELETE": request(base_url, "DELETE", f"/books/{ISBN}?format=json"),
        "GET_after_DELETE": request(base_url, "GET", f"/books/{ISBN}?format=json"),
    }
    result = {"name": name, "base_url": base_url, "isbn": ISBN, "steps": steps}
    (OUTPUT / f"cycle_{name.lower()}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    local = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5101"
    remote = sys.argv[2] if len(sys.argv) > 2 else "http://34.51.65.146:5001"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    results = [run_cycle("local", local), run_cycle("remote", remote)]
    print(json.dumps(results, ensure_ascii=False, indent=2))
