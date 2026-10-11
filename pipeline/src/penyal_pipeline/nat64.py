"""Reach IPv4-only hosts from an IPv6-only uplink through a NAT64 prefix (RFC 6052).

Some mobile hotspots (e.g. an IPv6-only carrier shared from a phone) forward IPv6 but drop
IPv4. A NAT64 gateway translates IPv6 packets addressed to ``<prefix>::<ipv4>`` into IPv4.
Only the TCP connection target changes: HTTP ``Host``, TLS SNI and certificate checks keep
using the original host name, so integrity and authenticity are unchanged.
"""

import http.client
import ipaddress
import socket
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

type Lookup = Callable[[str], list[str]]

# http.client passes this sentinel when no explicit timeout was given.
_DEFAULT_TIMEOUT: object = getattr(socket, "_GLOBAL_DEFAULT_TIMEOUT", object())


def parse_prefix(text: str) -> ipaddress.IPv6Network:
    """Parse a NAT64 prefix such as ``64:ff9b::/96``; only clean /96 prefixes are accepted."""
    try:
        network = ipaddress.ip_network(text, strict=True)
    except ValueError as exc:
        raise ValueError(
            f"{text!r} is not a NAT64 prefix; expected an IPv6 /96 network like 64:ff9b::/96"
        ) from exc
    if not isinstance(network, ipaddress.IPv6Network) or network.prefixlen != 96:
        raise ValueError(
            f"{text!r} is not a NAT64 prefix; expected an IPv6 /96 network like 64:ff9b::/96"
        )
    return network


def synthesize(prefix: ipaddress.IPv6Network, ipv4: ipaddress.IPv4Address) -> ipaddress.IPv6Address:
    """Embed ``ipv4`` in the low 32 bits of a /96 ``prefix`` (RFC 6052 §2.2)."""
    return ipaddress.IPv6Address(int(prefix.network_address) | int(ipv4))


def _is_native_ipv6(address: ipaddress.IPv6Address) -> bool:
    # macOS answers AF_INET6 lookups for IPv4-only hosts with IPv4-mapped addresses
    # (::ffff:a.b.c.d); dialing those goes out over IPv4, so they do not count as IPv6.
    return address.ipv4_mapped is None and not address.is_link_local


def _system_lookup(family: socket.AddressFamily) -> Lookup:
    def lookup(host: str) -> list[str]:
        try:
            infos = socket.getaddrinfo(host, None, family, socket.SOCK_STREAM)
        except socket.gaierror:
            return []
        seen: list[str] = []
        for info in infos:
            address = str(info[4][0])
            if address not in seen:
                seen.append(address)
        return seen

    return lookup


@dataclass(frozen=True)
class Nat64Resolver:
    """Picks IPv6 addresses for a host: native AAAA first, else synthesized from its A records."""

    prefix: ipaddress.IPv6Network
    lookup_ipv6: Lookup = field(default_factory=lambda: _system_lookup(socket.AF_INET6))
    lookup_ipv4: Lookup = field(default_factory=lambda: _system_lookup(socket.AF_INET))

    def addresses(self, host: str) -> list[str]:
        native = [a for a in self.lookup_ipv6(host) if _is_native_ipv6(ipaddress.IPv6Address(a))]
        if native:
            return native
        ipv4 = self.lookup_ipv4(host)
        if not ipv4:
            raise OSError(f"cannot resolve {host}: no AAAA or A records")
        return [str(synthesize(self.prefix, ipaddress.IPv4Address(a))) for a in ipv4]

    def create_connection(
        self,
        address: tuple[str, int],
        timeout: object = _DEFAULT_TIMEOUT,
        source_address: tuple[str, int] | None = None,
    ) -> socket.socket:
        """Drop-in for ``socket.create_connection`` that only dials IPv6."""
        host, port = address
        last_error: OSError | None = None
        for candidate in self.addresses(host):
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            try:
                if isinstance(timeout, int | float):
                    sock.settimeout(timeout)
                if source_address is not None:
                    sock.bind(source_address)
                sock.connect((candidate, port))
                return sock
            except OSError as exc:
                sock.close()
                last_error = exc
        raise last_error or OSError(f"no address to connect to {host}:{port}")

    def opener(self) -> urllib.request.OpenerDirector:
        """A urllib opener whose HTTP and HTTPS connections dial through this resolver."""
        dial = self.create_connection

        class _HTTPConnection(http.client.HTTPConnection):
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                super().__init__(*args, **kwargs)
                self._create_connection = dial  # pyright: ignore[reportAttributeAccessIssue]

        class _HTTPSConnection(http.client.HTTPSConnection):
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                super().__init__(*args, **kwargs)
                self._create_connection = dial  # pyright: ignore[reportAttributeAccessIssue]

        class _HTTPHandler(urllib.request.HTTPHandler):
            def http_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
                return self.do_open(_HTTPConnection, req)

        class _HTTPSHandler(urllib.request.HTTPSHandler):
            def https_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
                return self.do_open(_HTTPSConnection, req)

        return urllib.request.build_opener(_HTTPHandler(), _HTTPSHandler())
