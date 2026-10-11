import ipaddress
from pathlib import Path

import pytest
from conftest import FakeServer

from penyal_pipeline.fetch import Downloader
from penyal_pipeline.nat64 import Nat64Resolver, parse_prefix, synthesize

PAYLOAD = b"penyal" * 1000


def test_synthesize_matches_rfc6052_well_known_prefix_example() -> None:
    prefix = parse_prefix("64:ff9b::/96")
    assert synthesize(prefix, ipaddress.IPv4Address("192.0.2.33")) == ipaddress.IPv6Address(
        "64:ff9b::c000:221"
    )


def test_synthesize_matches_the_public_relay_observed_on_2026_10_11() -> None:
    prefix = parse_prefix("2a00:1098:2c::5:0:0/96")
    assert synthesize(prefix, ipaddress.IPv4Address("193.145.206.112")) == ipaddress.IPv6Address(
        "2a00:1098:2c::5:c191:ce70"
    )


@pytest.mark.parametrize("text", ["64:ff9b::/64", "64:ff9b::1/96", "192.0.2.0/24", "nonsense"])
def test_parse_prefix_rejects_anything_but_a_clean_ipv6_slash_96(text: str) -> None:
    with pytest.raises(ValueError, match="/96"):
        parse_prefix(text)


def test_resolver_prefers_native_ipv6_when_the_host_has_it() -> None:
    resolver = Nat64Resolver(
        parse_prefix("64:ff9b::/96"),
        lookup_ipv6=lambda host: ["2001:db8::7"],
        lookup_ipv4=lambda host: ["192.0.2.1"],
    )
    assert resolver.addresses("dual.test") == ["2001:db8::7"]


def test_resolver_synthesizes_for_ipv4_only_hosts() -> None:
    resolver = Nat64Resolver(
        parse_prefix("64:ff9b::/96"),
        lookup_ipv6=lambda host: [],
        lookup_ipv4=lambda host: ["192.0.2.33", "192.0.2.34"],
    )
    assert resolver.addresses("v4only.test") == ["64:ff9b::c000:221", "64:ff9b::c000:222"]


def test_resolver_ignores_ipv4_mapped_answers_and_synthesizes_instead() -> None:
    # macOS getaddrinfo(AF_INET6) answers ::ffff:a.b.c.d for IPv4-only hosts; dialing that
    # address goes out over IPv4, which is exactly what an IPv6-only uplink cannot do.
    resolver = Nat64Resolver(
        parse_prefix("64:ff9b::/96"),
        lookup_ipv6=lambda host: ["::ffff:192.0.2.33"],
        lookup_ipv4=lambda host: ["192.0.2.33"],
    )
    assert resolver.addresses("v4only.test") == ["64:ff9b::c000:221"]


def test_resolver_reports_unknown_hosts_actionably() -> None:
    resolver = Nat64Resolver(
        parse_prefix("64:ff9b::/96"), lookup_ipv6=lambda host: [], lookup_ipv4=lambda host: []
    )
    with pytest.raises(OSError, match=r"nowhere\.test"):
        resolver.addresses("nowhere.test")


def test_download_through_prefix_reaches_an_ipv4_only_server(
    server: FakeServer, sleeps: list[float], tmp_path: Path
) -> None:
    # The IPv4-mapped prefix ::ffff:0:0/96 turns 127.0.0.1 into ::ffff:127.0.0.1, which an IPv6
    # socket can reach on this machine: it exercises the same connection path as a real NAT64.
    server.files["/a.bin"] = PAYLOAD
    port = server.base_url.rsplit(":", 1)[1]
    resolver = Nat64Resolver(
        parse_prefix("::ffff:0:0/96"),
        lookup_ipv6=lambda host: [],
        lookup_ipv4=lambda host: ["127.0.0.1"] if host == "v4only.test" else [],
    )
    downloader = Downloader(
        timeout=5, retries=1, backoff=0.001, sleep=sleeps.append, nat64=resolver
    )
    record = downloader.download(f"http://v4only.test:{port}/a.bin", tmp_path / "a.bin")
    assert record.bytes == len(PAYLOAD)
    assert (tmp_path / "a.bin").read_bytes() == PAYLOAD
    assert server.requests[0][1]["Host"] == f"v4only.test:{port}"


def test_https_through_nat64_verifies_the_original_host_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The TCP target is an IPv6 address, but TLS must use the real host name for SNI and for
    the certificate check, otherwise NAT64 would weaken authenticity."""
    import socket
    import ssl
    import urllib.error

    seen: dict[str, object] = {}

    def fake_wrap(
        self: ssl.SSLContext, sock: socket.socket, *args: object, **kwargs: object
    ) -> ssl.SSLSocket:
        seen["server_hostname"] = kwargs.get("server_hostname")
        seen["peer"] = sock.getpeername()[0]
        raise ssl.SSLError("stop after the handshake parameters were captured")

    monkeypatch.setattr(ssl.SSLContext, "wrap_socket", fake_wrap)
    listener = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    listener.bind(("::1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    resolver = Nat64Resolver(
        parse_prefix("64:ff9b::/96"),
        lookup_ipv6=lambda host: [],
        lookup_ipv4=lambda host: ["192.0.2.1"],
    )
    synthesized = resolver.addresses("icv.example")
    assert synthesized == ["64:ff9b::c000:201"]
    # Dial the local listener instead of the unreachable synthesized address.
    dialer = Nat64Resolver(
        parse_prefix("64:ff9b::/96"),
        lookup_ipv6=lambda host: ["::1"],
        lookup_ipv4=lambda host: [],
    )
    try:
        with pytest.raises(urllib.error.URLError):
            dialer.opener().open(f"https://icv.example:{port}/x", timeout=5)
    finally:
        listener.close()
    assert seen["server_hostname"] == "icv.example"
    assert seen["peer"] == "::1"
    assert seen["server_hostname"] not in synthesized
