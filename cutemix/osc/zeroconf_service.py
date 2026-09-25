"""
Bonjour / Zeroconf Service Publisher for CuteMix.
Advertises an _osc._udp service so MOTU CueMix FX discovers the app
in 'Control Surfaces > TouchOSC' automatically.
"""

import socket
from typing import Optional

try:
    from zeroconf import IPVersion, ServiceInfo, Zeroconf
    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False


class CueMixZeroconfPublisher:
    """
    Publishes an mDNS/Bonjour service for CueMix FX auto-discovery.
    Uses '(TouchOSC)' suffix in the service name as expected by CueMix FX.
    """

    def __init__(self, service_name: str = "CuteMix 424 (TouchOSC)", port: int = 9000):
        self.service_name = service_name
        self.port = port
        self._zeroconf: Optional[object] = None
        self._service_info: Optional[object] = None
        self.is_advertising = False

    @staticmethod
    def is_supported() -> bool:
        return ZEROCONF_AVAILABLE

    def start(self) -> bool:
        if not ZEROCONF_AVAILABLE:
            return False

        if self.is_advertising:
            self.stop()

        try:
            # Determine local IP address
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            except Exception:
                local_ip = "127.0.0.1"
            finally:
                s.close()

            desc = {"txtvers": "1", "model": "PCI-424", "version": "1.0"}
            service_type = "_osc._udp.local."
            full_name = f"{self.service_name}.{service_type}"

            ip_bytes = socket.inet_aton(local_ip)

            self._service_info = ServiceInfo(
                type_=service_type,
                name=full_name,
                addresses=[ip_bytes],
                port=self.port,
                properties=desc,
                server=f"{socket.gethostname()}.local.",
            )

            self._zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
            self._zeroconf.register_service(self._service_info)
            self.is_advertising = True
            return True
        except Exception as e:
            self.is_advertising = False
            return False

    def stop(self):
        if not self.is_advertising:
            return

        try:
            if self._zeroconf and self._service_info:
                self._zeroconf.unregister_service(self._service_info)
                self._zeroconf.close()
        except Exception:
            pass
        finally:
            self._zeroconf = None
            self._service_info = None
            self.is_advertising = False
