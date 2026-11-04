# Per-host IP overrides

The Cambrian Firefox 157 fork supports an optional profile-local preference for directing a
hostname to a fixed IPv4 address while keeping the URL hostname, HTTP `Host`,
TLS SNI, and origin unchanged:

```text
network.host_overrides = "host.example=192.0.2.10,secure.example=192.0.2.11|insecure"
```

The default value is empty. Entries are comma-separated and use the exact
hostname form `hostname=IPv4`; the optional `|insecure` marker enables the
configured TLS verification bypass. Hostnames are matched
case-insensitively and with one trailing dot ignored. The mapping applies to
all ports for that hostname. IPv6 targets, wildcards, IP-literal hostnames,
non-ASCII host text, duplicate entries, malformed entries, and malformed
lists are rejected as a whole. Hosts absent from the list use ordinary DNS.

HTTPS RR/SVCB and Alt-Svc are suppressed for an overridden host, including
speculative connections. HTTP/HTTPS proxy, WebTransport, routed, and H3 connection
paths are rejected for overridden hosts. Existing HSTS processing remains in
force. Without `|insecure`, certificate verification is unchanged. With it,
only normally overridable certificate errors can be accepted, after existing
HSTS/static pinning guards, and only when the immutable socket snapshot,
current mapping, and socket-reported peer address all match. For SOCKS this is
the requested tunnel destination; see the proxy trust boundary below. This
stores no certificate exceptions and uses separate TLS session keys for each
address and TLS mode.
The response cache is unchanged. Use Ctrl+Shift+R (or `LOAD_BYPASS_CACHE`)
when a fresh network response is required.

Changing the preference clears DNS, Alt-Svc, TLS session/token state, and HTTP
connection pools. In-flight requests using those pools may be aborted. While
any override is configured, DNS-based cross-origin HTTP/2 and HTTP/3
coalescing is disabled globally; same-origin pooling remains keyed by the
normal connection identity plus the exact override address/mode.

The `|insecure` marker enables the configured TLS verification bypass for that
host and is shown as a conspicuous red `⚠ TLS bypass: hostname → IPv4` indicator beside the
identity control. Its tooltip says that TLS verification bypass is configured;
HSTS processing can still reject the connection. The indicator follows the
selected top-level tab and updates when the preference changes. It is status
only and provides no management controls.

The indicator describes the current configuration. A previously loaded or
cached response can still be displayed after an edit; reload to exercise the
new destination. Closing existing connections is asynchronous across processes,
so in-flight requests may be interrupted rather than instantly migrated.
Pinned-certificate mode and a management page are not implemented.

## SOCKS proxies

Mapped hosts support SOCKS4 and SOCKS5, with proxy DNS enabled or disabled. Keep
using Firefox's existing proxy settings; there is no new override preference.
The selected SOCKS proxy receives the configured IPv4 destination and original
port. It receives a numeric address rather than resolving the mapped hostname.
The browser retains the original URL, HTTP Host/authority, TLS SNI and certificate
hostname, cookies and web origin. Unmapped hosts retain ordinary SOCKS behavior.

The SOCKS connection captures its mapping when initialized. Preference changes
retain the existing connection invalidation and TLS snapshot/session protections.
SOCKS authentication and proxy selection continue through Firefox's existing
implementation. HTTP and HTTPS forward proxies remain unsupported for mapped
hosts; SOCKS support does not bypass the selected proxy to connect directly.

For direct connections, the TLS peer check identifies the TCP peer. With SOCKS,
the socket layer reports the requested tunnel destination; the proxy is trusted
to forward to that destination. Strict TLS still verifies the origin certificate
end to end. Explicit `|insecure` retains its existing error, HSTS, pinning,
immutable-snapshot and current-mapping checks, with that tunnel destination as
the peer address. It does not authenticate a server independently of the proxy.

Mapped SOCKS connections retain the network-state origin attributes used by
HSTS storage, even when ordinary proxy connections use an unpartitioned
identity. This keeps the TLS override gate aligned with learned HSTS policy
and partitions the associated connections and sessions consistently. No global
proxy-partitioning preference is changed.
