import http.server
import json
import socketserver
import threading
import time
from urllib.parse import urlparse, parse_qs


class MockControlIdHandler(http.server.BaseHTTPRequestHandler):
    """Manipulador HTTP simulando equipamentos Control iD com autenticação."""

    def log_message(self, format, *args):
        # Silencia logs no terminal para não poluir testes
        pass

    def _send_json(self, status: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        content_len = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_len) if content_len > 0 else b""
        payload = {}
        if post_data:
            try:
                payload = json.loads(post_data.decode("utf-8"))
            except Exception:
                pass

        if path == "/login.fcgi":
            login = payload.get("login")
            pwd = payload.get("password")
            if login == "admin" and pwd == "admin":
                self._send_json(200, {"session": "mock_valid_session_123"})
            else:
                self._send_json(401, {"error": "Credenciais inválidas"})
            return

        if path == "/logout.fcgi":
            self._send_json(200, {"status": "success"})
            return

        if path == "/system_information.fcgi":
            session = query.get("session", [None])[0]
            # Simula retorno autenticado
            data = {
                "serial": "100200300400500",
                "device_id": "100200300400500",
                "version": "2.4.1",
                "model": "iDFace",
                "mac": "00:1A:2B:3C:4D:5E",
                "uptime": 128450
            }
            self._send_json(200, data)
            return

        self.send_response(404)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        device_type = query.get("type", ["idface"])[0]

        if path == "/system_information.fcgi":
            if device_type == "slow":
                time.sleep(2.0)

            if device_type == "error":
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Internal Server Error")
                return

            if device_type == "other_device":
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><head><title>Generic Router</title></head><body>Welcome</body></html>")
                return

            if device_type == "auth_required":
                # Simula equipamento que exige login
                session = query.get("session", [None])[0]
                if session == "mock_valid_session_123":
                    payload = {
                        "serial": "100200300400500",
                        "model": "iDFace",
                        "version": "2.4.1"
                    }
                    self._send_json(200, payload)
                else:
                    self.send_response(401)
                    self.end_headers()
                    self.wfile.write(b"Unauthorized - Login Required")
                return

            if device_type == "idclass":
                payload = {
                    "serial_number": "0000000012345678",
                    "device_model": "iDClass",
                    "firmware_version": "1.1.25",
                    "hardware_version": "REV_C"
                }
            else:  # default idface
                payload = {
                    "serial": "100200300400500",
                    "device_id": "100200300400500",
                    "version": "2.4.1",
                    "model": "iDFace",
                    "mac": "00:1A:2B:3C:4D:5E",
                    "uptime": 128450
                }

            self._send_json(200, payload)

        elif path == "/api/system/information":
            payload = {
                "status": "success",
                "data": {
                    "serialNumber": "9876543210",
                    "modelName": "iDAccess Pro",
                    "softwareVersion": "3.0.2"
                }
            }
            self._send_json(200, payload)

        elif path in ("/login.fcgi", "/"):
            html = "<html><head><title>Control iD - iDFace</title></head><body>Login Control iD</body></html>"
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")


class MockServerThread:
    """Helper para iniciar o Mock Server em uma thread de background."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8089):
        self.host = host
        self.port = port
        self.httpd = socketserver.TCPServer((self.host, self.port), MockControlIdHandler)
        self.httpd.allow_reuse_address = True
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()


if __name__ == "__main__":
    server = MockServerThread("127.0.0.1", 8089)
    server.start()
    print("Mock Control iD Server rodando em http://127.0.0.1:8089 (Pressione Ctrl+C para parar)...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
        print("Servidor finalizado.")
