from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import re

from comparison_service import compare_documents
from cluster_service import (
    available_countries,
    extract_submatrix,
    register_custom_country,
    run_clustering as _run_clustering,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
UI_DIR = PROJECT_ROOT / "ui"
DATA_DIR = PROJECT_ROOT / "data"
HOST = "127.0.0.1"
PORT = 8765


def json_response(handler: BaseHTTPRequestHandler, payload: dict, status: int = HTTPStatus.OK) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def text_response(handler: BaseHTTPRequestHandler, text: str, content_type: str = "text/plain; charset=utf-8") -> None:
    body = text.encode("utf-8")
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def list_relative_files(folder: Path, suffix: str) -> list[str]:
    if not folder.exists():
        return []
    files = [path.relative_to(PROJECT_ROOT).as_posix() for path in folder.glob(f"*{suffix}") if path.is_file()]
    return sorted(files)


def safe_project_path(relative_path: str) -> Path:
    path = (PROJECT_ROOT / relative_path).resolve()
    if PROJECT_ROOT not in path.parents and path != PROJECT_ROOT:
        raise ValueError("Path escapes project root.")
    return path


def read_static_file(request_path: str) -> tuple[bytes, str] | None:
    relative = request_path.lstrip("/") or "index.html"
    if relative == "":
        relative = "index.html"

    file_path = (UI_DIR / relative).resolve()
    if UI_DIR not in file_path.parents and file_path != UI_DIR / "index.html":
        return None
    if not file_path.exists() or not file_path.is_file():
        return None

    suffix_map = {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".svg": "image/svg+xml",
    }
    content_type = suffix_map.get(file_path.suffix.lower(), "application/octet-stream")
    return file_path.read_bytes(), content_type


class UIRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if parsed.path == "/api/cluster/countries":
            try:
                countries = available_countries()
                json_response(self, {"countries": countries})
            except Exception as exc:
                json_response(self, {"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if parsed.path == "/api/options":
            payload = {
                "methods": ["custom", "chawathe", "nj"],
                "modes": {
                    "xml": {
                        "files": list_relative_files(DATA_DIR / "normalized_xml", ".xml"),
                    },
                    "wiki": {
                        "files": list_relative_files(DATA_DIR / "original_infobox_source", ".wiki"),
                    },
                },
            }
            json_response(self, payload)
            return

        if parsed.path == "/api/file":
            query = parse_qs(parsed.query)
            relative_path = query.get("path", [""])[0]
            if not relative_path:
                json_response(self, {"error": "Missing path parameter."}, status=HTTPStatus.BAD_REQUEST)
                return

            try:
                file_path = safe_project_path(relative_path)
            except ValueError:
                json_response(self, {"error": "Invalid path."}, status=HTTPStatus.BAD_REQUEST)
                return

            if not file_path.exists() or not file_path.is_file():
                json_response(self, {"error": "File not found."}, status=HTTPStatus.NOT_FOUND)
                return

            text_response(self, file_path.read_text(encoding="utf-8"))
            return

        static = read_static_file(parsed.path if parsed.path != "/" else "/index.html")
        if static is None:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        body, content_type = static
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if parsed.path == "/api/add_country":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length)
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except json.JSONDecodeError:
                json_response(self, {"error": "Invalid JSON."}, status=HTTPStatus.BAD_REQUEST)
                return

            raw_name = str(payload.get("name", "")).strip().lower()
            xml_content = str(payload.get("xml", "")).strip()

            # Normalise name to snake_case
            name = re.sub(r"[^a-z0-9]+", "_", raw_name).strip("_")
            if not name:
                json_response(self, {"error": "Country name is required."}, status=HTTPStatus.BAD_REQUEST)
                return
            if not xml_content:
                json_response(self, {"error": "XML content is required."}, status=HTTPStatus.BAD_REQUEST)
                return

            # Basic XML syntax check
            try:
                import xml.etree.ElementTree as ET
                ET.fromstring(xml_content)
            except ET.ParseError as exc:
                json_response(self, {"error": f"Invalid XML: {exc}"}, status=HTTPStatus.BAD_REQUEST)
                return

            dest = DATA_DIR / "normalized_xml" / f"{name}.xml"
            dest.write_text(xml_content, encoding="utf-8")

            # Preprocess and gather metadata
            try:
                import sys
                sys.path.insert(0, os.fspath(PROJECT_ROOT / "src"))
                from parser import parse_xml_file
                from preprocess import preprocess_tree
                from utils import count_nodes

                tree = preprocess_tree(parse_xml_file(os.fspath(dest)))
                node_count = count_nodes(tree)
                fields = [c.label for c in tree.children]
            except Exception as exc:
                dest.unlink(missing_ok=True)
                json_response(self, {"error": f"Parse/preprocess failed: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return

            register_custom_country(name, dest)
            json_response(self, {
                "name": name,
                "path": f"data/normalized_xml/{name}.xml",
                "node_count": node_count,
                "fields": fields,
            })
            return

        if parsed.path == "/api/cluster/run":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length)
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except json.JSONDecodeError:
                json_response(self, {"error": "Invalid JSON."}, status=HTTPStatus.BAD_REQUEST)
                return

            selected = payload.get("countries", [])
            algorithm = str(payload.get("algorithm", "ahc")).lower()
            params = payload.get("params", {})

            if not selected or not isinstance(selected, list):
                json_response(self, {"error": "countries must be a non-empty list."}, status=HTTPStatus.BAD_REQUEST)
                return
            if algorithm not in {"ahc", "kmedoids", "kmeans", "dbscan"}:
                json_response(self, {"error": f"Unknown algorithm: {algorithm}"}, status=HTTPStatus.BAD_REQUEST)
                return

            try:
                matrix = extract_submatrix(selected)
                result = _run_clustering(selected, matrix, algorithm, params)
                json_response(self, result)
            except Exception as exc:
                json_response(self, {"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if parsed.path != "/api/compare":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            json_response(self, {"error": "Invalid JSON body."}, status=HTTPStatus.BAD_REQUEST)
            return

        mode = str(payload.get("mode", "")).lower()
        method = str(payload.get("method", "custom")).lower()
        file1 = str(payload.get("file1", ""))
        file2 = str(payload.get("file2", ""))

        if mode not in {"xml", "wiki"}:
            json_response(self, {"error": "Mode must be xml or wiki."}, status=HTTPStatus.BAD_REQUEST)
            return
        if method not in {"custom", "chawathe", "nj"}:
            json_response(self, {"error": "Unsupported method."}, status=HTTPStatus.BAD_REQUEST)
            return
        if not file1 or not file2:
            json_response(self, {"error": "Both file selections are required."}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            abs_file1 = safe_project_path(file1)
            abs_file2 = safe_project_path(file2)
        except ValueError:
            json_response(self, {"error": "Invalid file path."}, status=HTTPStatus.BAD_REQUEST)
            return

        if not abs_file1.exists() or not abs_file2.exists():
            json_response(self, {"error": "Selected file does not exist."}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            result = compare_documents(
                mode=mode,
                file1=os.fspath(abs_file1),
                file2=os.fspath(abs_file2),
                method=method,
                output_dir=os.fspath(DATA_DIR / "output"),
            )
        except Exception as exc:  # pragma: no cover - defensive API path
            json_response(self, {"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        json_response(self, result)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), UIRequestHandler)
    print(f"Project UI available at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop the server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down UI server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
