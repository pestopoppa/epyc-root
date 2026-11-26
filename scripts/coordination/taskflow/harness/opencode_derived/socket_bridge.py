"""Expose the case's private Unix model socket on container loopback."""
import select
import socket
import socketserver
import sys
import threading


def relay(first, second):
    readable = [first, second]
    while readable:
        ready, _, _ = select.select(readable, [], [], 900)
        if not ready:
            return
        for source in ready:
            target = second if source is first else first
            data = source.recv(65536)
            try:
                if data:
                    target.sendall(data)
                else:
                    readable.remove(source)
                    target.shutdown(socket.SHUT_WR)
            except (BrokenPipeError, ConnectionResetError):
                # The client disconnected or the case watchdog closed the request.
                # The model adapter records request status separately.
                return


class LocalBridge(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


class LocalHandler(socketserver.BaseRequestHandler):
    def handle(self):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as model:
            model.connect(self.server.socket_path)
            relay(self.request, model)


if __name__ == "__main__":
    with LocalBridge(("127.0.0.1", 8101), LocalHandler) as server:
        server.socket_path = sys.argv[1]
        if len(sys.argv) == 3:
            web = LocalBridge(("127.0.0.1", 8102), LocalHandler)
            web.socket_path = sys.argv[2]
            threading.Thread(target=web.serve_forever, daemon=True).start()
        print("case model bridge ready", flush=True)
        server.serve_forever()
