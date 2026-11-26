"""Public HTTP(S) for network-isolated cases. No private or host route."""
from contextlib import closing
import http.client
from http.server import BaseHTTPRequestHandler
import ipaddress
import socket
from urllib.parse import urlsplit

from .socket_bridge import relay


def addresses(host, port):
    if not host or host.endswith((".local", ".internal", ".localhost")) or "." not in host:
        raise PermissionError("web gateway requires a public Internet hostname")
    options = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    for _, _, _, _, address in options:
        ip = ipaddress.ip_address(address[0])
        if not ip.is_global or ip.is_multicast or ip.is_reserved:
            raise PermissionError("web gateway refuses nonpublic addresses")
    return options


def public_connection(host, port):
    for family, kind, proto, _, address in addresses(host, port):
        upstream = socket.socket(family, kind, proto)
        try:
            upstream.settimeout(15)
            upstream.connect(address)
            return upstream
        except OSError:
            upstream.close()
    raise OSError("public endpoint unavailable")


class PublicWebHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, *_):
        pass

    def fail(self, error):
        self.send_error(403 if isinstance(error, PermissionError) else 502, str(error))

    def do_CONNECT(self):
        try:
            dest = urlsplit("//" + self.path)
            if dest.port != 443 or dest.username or dest.path or dest.query or dest.fragment:
                raise PermissionError("HTTPS only over TCP port 443")
            upstream = public_connection(dest.hostname, dest.port)
        except (OSError, ValueError) as error:
            self.fail(error)
            return
        with closing(upstream):
            self.send_response_only(200, "Connection Established")
            self.end_headers()
            try:
                relay(self.connection, upstream)
            except (ConnectionError, TimeoutError):
                pass

    def read_only(self):
        dest = urlsplit(self.path)
        try:
            if (dest.scheme != "http" or dest.port not in (None, 80) or dest.username
                    or dest.fragment or self.headers.get("Content-Length", "0") != "0"):
                raise PermissionError("only public, read-only HTTP requests are permitted")
            upstream = public_connection(dest.hostname, 80)
        except (OSError, ValueError) as error:
            self.fail(error)
            return
        with closing(http.client.HTTPConnection(dest.hostname, 80)) as client:
            client.sock = upstream
            path = dest.path or "/"
            if dest.query:
                path += "?" + dest.query
            headers = {"User-Agent": self.headers.get("User-Agent", "OpenCode"), "Accept": "*/*", "Connection": "close"}
            client.request(self.command, path, headers=headers)
            with closing(client.getresponse()) as response:
                self.send_response(response.status, response.reason)
                for name, value in response.getheaders():
                    if name.lower() not in {"connection", "transfer-encoding", "proxy-authenticate", "set-cookie"}:
                        self.send_header(name, value)
                self.end_headers()
                if self.command != "HEAD":
                    while data := response.read(65536):
                        self.wfile.write(data)

    do_GET = do_HEAD = read_only
