"""Run real Streamlit behind an HTTP-only browser transport (no public WebSocket)."""

import argparse
import asyncio
import base64
import json
import logging
import secrets
import signal
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import tornado.httpclient
import tornado.web
import tornado.websocket

PREFIX = "/_greenhouse_transport"
MAX_MESSAGE = 16 * 1024 * 1024
IDLE_SECONDS = 90


class Session:
    def __init__(self, socket):
        self.socket = socket
        self.queue = asyncio.Queue(maxsize=128)
        self.last_seen = time.monotonic()
        self.closed = False
        self.polling = False
        self.queued_bytes = 0
        self.task = asyncio.create_task(self.receive())

    async def receive(self):
        try:
            while True:
                message = await self.socket.read_message()
                if message is None:
                    break
                binary = isinstance(message, bytes)
                data = base64.b64encode(message).decode() if binary else message
                if self.queued_bytes + len(data) > 32 * 1024 * 1024:
                    self.socket.close(code=1009, reason="HTTP client is too slow")
                    break
                self.queued_bytes += len(data)
                await self.queue.put({"binary": binary, "data": data})
        except tornado.websocket.WebSocketClosedError:
            pass
        finally:
            self.closed = True

    def close(self):
        self.closed = True
        self.socket.close()
        self.task.cancel()


class Transport(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Cache-Control", "no-store")
        self.set_header("X-Content-Type-Options", "nosniff")

    def prepare(self):
        # JSON plus the custom header prevent cross-site form submissions. No CORS.
        if self.request.headers.get("X-Greenhouse-Transport") != "1":
            raise tornado.web.HTTPError(403)
        origin = self.request.headers.get("Origin")
        if origin and urlsplit(origin).netloc != self.request.host:
            raise tornado.web.HTTPError(403)

    async def post(self, token=None):
        try:
            data = json.loads(self.request.body or b"{}")
            if not isinstance(data, dict):
                raise ValueError()
        except (ValueError, TypeError):
            raise tornado.web.HTTPError(400)
        sessions = self.application.sessions
        if token is None:
            if len(sessions) >= 100:
                raise tornado.web.HTTPError(503, "Too many sessions")
            protocols = data.get("protocols", [])
            if not isinstance(protocols, list) or not all(isinstance(p, str) for p in protocols):
                raise tornado.web.HTTPError(400)
            # Only a fixed local endpoint is connectable; the browser supplies no URL.
            headers = {"Host": self.request.host}
            for name in ("Cookie", "Origin"):
                if name in self.request.headers:
                    headers[name] = self.request.headers[name]
            request = tornado.httpclient.HTTPRequest(
                self.application.upstream.replace("http://", "ws://") + "/_stcore/stream",
                headers=headers, connect_timeout=10)
            try:
                socket = await tornado.websocket.websocket_connect(
                    request, subprotocols=protocols, max_message_size=MAX_MESSAGE,
                    ping_interval=20, ping_timeout=30)
            except Exception:
                logging.exception("Local Streamlit WebSocket connection failed")
                raise tornado.web.HTTPError(502, "Streamlit connection failed")
            token = secrets.token_urlsafe(32)
            sessions[token] = Session(socket)
            self.write({"id": token, "protocol": socket.selected_subprotocol or ""})
            return
        session = sessions.get(token)
        if session is None:
            raise tornado.web.HTTPError(404)
        session.last_seen = time.monotonic()
        action = data.get("action")
        if action == "close":
            sessions.pop(token).close()
            self.write({})
        elif action == "send":
            if session.closed:
                raise tornado.web.HTTPError(410)
            message = data.get("data")
            if not isinstance(message, str):
                raise tornado.web.HTTPError(400)
            binary = data.get("binary") is True
            if binary:
                try:
                    message = base64.b64decode(message, validate=True)
                except ValueError:
                    raise tornado.web.HTTPError(400)
            if len(message) > MAX_MESSAGE:
                raise tornado.web.HTTPError(413)
            await session.socket.write_message(message, binary=binary)
            self.write({})
        elif action == "poll":
            if session.polling:
                raise tornado.web.HTTPError(409)
            session.polling = True
            messages = []
            try:
                # Short, finite responses also work through buffering proxies.
                if session.queue.empty() and not session.closed:
                    try:
                        messages.append(await asyncio.wait_for(session.queue.get(), 1))
                    except asyncio.TimeoutError:
                        pass
                while not session.queue.empty() and len(messages) < 16:
                    messages.append(session.queue.get_nowait())
                session.queued_bytes -= sum(len(message["data"]) for message in messages)
                self.write({"messages": messages,
                            "closed": session.closed and session.queue.empty()})
            finally:
                session.polling = False
                session.last_seen = time.monotonic()
        else:
            raise tornado.web.HTTPError(400)


class Adapter(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/javascript")
        self.set_header("Cache-Control", "no-store")
        self.write(Path(__file__).with_name("http_transport.js").read_bytes())


class Proxy(tornado.web.RequestHandler):
    async def get(self):
        await self.forward()

    async def head(self):
        await self.forward()

    async def post(self):
        await self.forward()

    async def put(self):
        await self.forward()

    async def delete(self):
        await self.forward()

    async def forward(self):
        headers = self.request.headers.copy()
        for name in ("Connection", "Upgrade", "Accept-Encoding", "Content-Length",
                     "If-None-Match", "If-Modified-Since"):
            headers.pop(name, None)
        try:
            response = await tornado.httpclient.AsyncHTTPClient().fetch(
                tornado.httpclient.HTTPRequest(
                    self.application.upstream + self.request.uri,
                    method=self.request.method, headers=headers,
                    body=self.request.body if self.request.method in ("POST", "PUT", "PATCH") else None,
                    follow_redirects=False, request_timeout=120), raise_error=False)
        except (OSError, tornado.httpclient.HTTPClientError):
            raise tornado.web.HTTPError(502, "Streamlit is unavailable")
        body = response.body
        html = "text/html" in response.headers.get("Content-Type", "")
        if html and self.request.method != "HEAD":
            injection = ('<script src="' + PREFIX + '/adapter.js"></script>').encode()
            body = body.replace(b"<head>", b"<head>" + injection, 1)
        self.set_status(response.code)
        for name, value in response.headers.get_all():
            if name.lower() not in ("content-length", "transfer-encoding", "connection",
                                     "content-encoding", "etag", "cache-control"):
                if name.lower() == "set-cookie":
                    self.add_header(name, value)
                else:
                    self.set_header(name, value)
        if html:
            self.set_header("Cache-Control", "no-store")
        elif "Cache-Control" in response.headers:
            self.set_header("Cache-Control", response.headers["Cache-Control"])
        if self.request.method != "HEAD" and response.code not in (204, 304):
            self.write(body)


def make_app(upstream):
    app = tornado.web.Application([
        (PREFIX + r"/adapter\.js", Adapter),
        (PREFIX + r"/session(?:/([A-Za-z0-9_-]+))?", Transport),
        (r"/.*", Proxy),
    ])
    app.upstream = upstream
    app.sessions = {}
    return app


async def run(args):
    if args.port == args.streamlit_port:
        raise SystemExit("Bridge and Streamlit ports must differ")
    child = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "streamlit", "run", args.app,
        "--server.address=127.0.0.1", "--server.port=" + str(args.streamlit_port),
        "--server.headless=true", "--browser.gatherUsageStats=false")
    app = make_app("http://127.0.0.1:" + str(args.streamlit_port))
    server = app.listen(args.port, address=args.address, max_buffer_size=24 * 1024 * 1024)
    stopping = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stopping.set)

    async def reap():
        while not stopping.is_set():
            for token, session in list(app.sessions.items()):
                if time.monotonic() - session.last_seen > IDLE_SECONDS:
                    app.sessions.pop(token).close()
            await asyncio.sleep(5)

    reaper = asyncio.create_task(reap())
    child_wait = asyncio.create_task(child.wait())
    stop_wait = asyncio.create_task(stopping.wait())
    try:
        await asyncio.wait([child_wait, stop_wait], return_when=asyncio.FIRST_COMPLETED)
    finally:
        server.stop()
        reaper.cancel()
        stop_wait.cancel()
        for session in app.sessions.values():
            session.close()
        if child.returncode is None:
            child.terminate()
            try:
                await asyncio.wait_for(asyncio.shield(child_wait), 10)
            except asyncio.TimeoutError:
                child.kill()
                await child_wait
    if child.returncode:
        raise SystemExit(child.returncode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--address", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--streamlit-port", type=int, default=8502)
    parser.add_argument("--app", default="app.py")
    asyncio.run(run(parser.parse_args()))
