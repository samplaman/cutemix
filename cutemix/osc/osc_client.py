"""
Asynchronous UDP OSC Network Engine.
Provides bidirectional OSC communication with CueMix FX or any OSC device.
Thread-safe send and receive with background listener.
"""

import socket
import select
import threading
import time
from typing import Callable, List, Optional, Tuple, Union
from .osc_core import OscMessage, OscBundle, decode_packet, OscDecodeError


class OscLogEntry:
    def __init__(self, direction: str, address: str, args: list, raw_bytes: bytes, remote_addr: Tuple[str, int]):
        self.timestamp = time.time()
        self.direction = direction  # "IN" or "OUT"
        self.address = address
        self.args = args
        self.raw_bytes = raw_bytes
        self.remote_addr = remote_addr

    def formatted_time(self) -> str:
        t = time.localtime(self.timestamp)
        millis = int((self.timestamp - int(self.timestamp)) * 1000)
        return f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}.{millis:03d}"


class OscClient:
    """
    Manages UDP socket sending and listening for OSC communication.
    Works independently or integrated with Qt signals.
    """

    def __init__(self, target_host: str = "127.0.0.1", target_port: int = 8000, listen_port: int = 9000):
        self.target_host = target_host
        self.target_port = target_port
        self.listen_port = listen_port

        self._send_sock: Optional[socket.socket] = None
        self._listen_sock: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Callbacks
        self.on_message_received: Optional[Callable[[OscMessage, Tuple[str, int]], None]] = None
        self.on_packet_logged: Optional[Callable[[OscLogEntry], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

        # Statistics
        self.packets_sent = 0
        self.packets_received = 0
        self.bytes_sent = 0
        self.bytes_received = 0
        self.last_sent_time: float = 0.0
        self.last_recv_time: float = 0.0

    def start(self) -> bool:
        """Starts the UDP listener and initializes the send socket."""
        self.stop()

        try:
            # Send socket
            self._send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Listen socket
            self._listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Bind to all interfaces on listen_port
            self._listen_sock.bind(("", self.listen_port))
            self._listen_sock.setblocking(False)

            self._running = True
            self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="CuteMix-OscListener")
            self._thread.start()
            return True
        except Exception as e:
            if self.on_error:
                self.on_error(f"Failed to start OSC socket: {e}")
            self.stop()
            return False

    def stop(self):
        """Stops the listener and closes sockets."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.3)
        self._thread = None

        if self._listen_sock:
            try:
                self._listen_sock.close()
            except Exception:
                pass
            self._listen_sock = None

        if self._send_sock:
            try:
                self._send_sock.close()
            except Exception:
                pass
            self._send_sock = None

    def is_running(self) -> bool:
        return self._running and self._listen_sock is not None

    def update_config(self, target_host: str, target_port: int, listen_port: int) -> bool:
        """Updates network configuration. Restarts listener if listen_port changed."""
        port_changed = (listen_port != self.listen_port)
        self.target_host = target_host
        self.target_port = target_port
        self.listen_port = listen_port

        if port_changed and self._running:
            return self.start()
        return True

    def send_message(self, message: OscMessage) -> bool:
        """Encodes and sends an OscMessage via UDP to the target endpoint."""
        if not self._send_sock:
            try:
                self._send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            except Exception as e:
                if self.on_error:
                    self.on_error(f"Socket error: {e}")
                return False

        try:
            raw = message.encode()
            self._send_sock.sendto(raw, (self.target_host, self.target_port))
            self.packets_sent += 1
            self.bytes_sent += len(raw)
            self.last_sent_time = time.time()

            if self.on_packet_logged:
                entry = OscLogEntry(
                    direction="OUT",
                    address=message.address,
                    args=message.args,
                    raw_bytes=raw,
                    remote_addr=(self.target_host, self.target_port),
                )
                self.on_packet_logged(entry)
            return True
        except Exception as e:
            if self.on_error:
                self.on_error(f"Send error: {e}")
            return False

    def send_messages(self, messages: List[OscMessage]):
        for msg in messages:
            self.send_message(msg)

    def _listen_loop(self):
        """Worker loop listening for incoming UDP OSC packets."""
        while self._running and self._listen_sock:
            try:
                r, _, _ = select.select([self._listen_sock], [], [], 0.05)
                if not r:
                    continue
                data, addr = self._listen_sock.recvfrom(65535)
                if not data:
                    continue

                self.packets_received += 1
                self.bytes_received += len(data)
                self.last_recv_time = time.time()

                try:
                    packet = decode_packet(data)
                    self._dispatch_packet(packet, data, addr)
                except OscDecodeError as de:
                    if self.on_error:
                        self.on_error(f"OSC Decode error from {addr}: {de}")
            except (socket.error, OSError) as se:
                if self._running and self.on_error:
                    self.on_error(f"OSC socket receive error: {se}")
                break

    def _dispatch_packet(self, packet: Union[OscMessage, OscBundle], raw_bytes: bytes, addr: Tuple[str, int]):
        if isinstance(packet, OscMessage):
            if self.on_packet_logged:
                entry = OscLogEntry("IN", packet.address, packet.args, raw_bytes, addr)
                self.on_packet_logged(entry)
            if self.on_message_received:
                self.on_message_received(packet, addr)
        elif isinstance(packet, OscBundle):
            for elem in packet.elements:
                self._dispatch_packet(elem, raw_bytes, addr)
