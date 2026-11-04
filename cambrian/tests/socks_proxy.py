"""Loopback-only SOCKS4/4a/5 fixture with observable destination requests."""
import select
import socket
import socketserver
import struct
import threading


def read_exact(sock, size):
    value = b""
    while len(value) < size:
        chunk = sock.recv(size - len(value))
        if not chunk:
            raise EOFError("Incomplete SOCKS request")
        value += chunk
    return value


def read_string(sock):
    value = bytearray()
    for _ in range(256):
        char = read_exact(sock, 1)
        if char == b"\0":
            return value.decode("ascii")
        value.extend(char)
    raise ValueError("SOCKS string too long")


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        client = self.request
        client.settimeout(10)
        upstream = None
        try:
            version = read_exact(client, 1)[0]
            if version == 4:
                command, port = struct.unpack("!BH", read_exact(client, 3))
                address = read_exact(client, 4)
                read_string(client)
                domain = address[:3] == b"\0\0\0" and address[3] != 0
                host = read_string(client) if domain else socket.inet_ntoa(address)
            elif version == 5:
                methods = read_exact(client, read_exact(client, 1)[0])
                if 0 not in methods:
                    client.sendall(b"\x05\xff")
                    return
                client.sendall(b"\x05\x00")
                protocol, command, reserved, address_type = read_exact(client, 4)
                if protocol != 5 or reserved:
                    raise ValueError("Invalid SOCKS5 header")
                domain = address_type == 3
                if domain:
                    host = read_exact(client, read_exact(client, 1)[0]).decode("ascii")
                elif address_type == 1:
                    host = socket.inet_ntoa(read_exact(client, 4))
                elif address_type == 4:
                    host = socket.inet_ntop(socket.AF_INET6, read_exact(client, 16))
                else:
                    raise ValueError("Unsupported address type")
                port = struct.unpack("!H", read_exact(client, 2))[0]
            else:
                raise ValueError("Unsupported SOCKS version")
            record = {"version": version, "host": host, "port": port, "domain": domain}
            self.server.records.append(record)
            address = "127.0.0.1" if host == "localhost" else host
            if command != 1 or address not in {"127.0.0.1", "127.0.0.2"} or port not in self.server.allowed_ports:
                record["rejected"] = True
                client.sendall(b"\x00\x5b" + b"\0" * 6 if version == 4 else b"\x05\x04\x00\x01" + b"\0" * 6)
                return
            upstream = socket.create_connection((address, port), timeout=10, source_address=("127.0.0.3", 0))
            record["connected"] = True
            client.sendall(b"\x00\x5a" + b"\0" * 6 if version == 4 else b"\x05\x00\x00\x01" + b"\0" * 6)
            client.settimeout(None)
            upstream.settimeout(None)
            while not self.server.stopping.is_set():
                readable, _, _ = select.select([client, upstream], [], [], .2)
                for source in readable:
                    data = source.recv(65536)
                    if not data:
                        return
                    (upstream if source is client else client).sendall(data)
        except (OSError, EOFError, ValueError):
            pass
        finally:
            if upstream:
                upstream.close()


class SocksProxy(socketserver.ThreadingTCPServer):
    daemon_threads = True

    def __init__(self, allowed_ports, host="127.0.0.1"):
        self.address_family = socket.AF_INET6 if ":" in host else socket.AF_INET
        super().__init__((host, 0), Handler)
        self.allowed_ports = set(allowed_ports)
        self.records = []
        self.stopping = threading.Event()
        self.thread = threading.Thread(target=self.serve_forever, daemon=True)
        self.thread.start()

    @property
    def port(self):
        return self.server_address[1]

    def close(self):
        self.stopping.set()
        self.shutdown()
        self.server_close()
        self.thread.join(timeout=5)
