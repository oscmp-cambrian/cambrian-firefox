# Prototype validation and change summary

Baseline: Firefox 157.0, upstream `FIREFOX_157_0_RELEASE`
(`fdd757a2e09c9471cddf383e64e631e4ce178499`). That increment was developed on
`feature/host-overrides`; the archive's `manifest.json` records its exact source
revision, compiler versions and actual verification mozconfig.

## Completed checks

Executed on Ubuntu Linux x86_64, using a native optimized build with tests
compiled, fresh browser profiles and `acceptInsecureCerts=false`:

| Required check (Agent) | Result | Evidence |
| --- | --- | --- |
| Native build | Passed | `logs/build-final.log`, final successful run |
| DNS xpcshell regression | Passed, 29 subtests | `logs/xpcshell-host-overrides.log` |
| Immutable TLS snapshot/session-key GTests | Passed, 2 tests | `logs/gtest-hostoverride.log` |
| Existing TLS session-resumption regression | Passed, 154 subtests | `logs/xpcshell-session-resumption.log` |
| Existing private-browsing session-cache regression | Passed, 17 subtests | `logs/xpcshell-pbm.log` |
| Browser matrix, socket process on | Passed, 33 checks | `logs/browser-socket.json` and sibling resolver logs |
| Browser matrix, socket process off | Passed, 33 checks | `logs/browser-parent.json` and sibling resolver logs |
| ESLint / preference lint / whitespace checks | Passed | `logs/final-eslint.log`, source worker lint checks |

Logs are under `/home/codex/builds/cambrian-firefox-host-overrides/`; reproducible
commands and fixture prerequisites are in `cambrian/tests/README.md`.
The browser matrices confirm actual socket-process PID/on and absent/off, mapped
TCP destination `127.0.0.2`, original Host/authority and SNI, HTTP/1.1 and H2,
WS/WSS Origin, redirects, cookies, same-origin/CORS, ordinary-host controls,
synthetic DNS A/suppressed HTTPS records with no actual resolver dispatch,
Alt-Svc trap avoidance, live-proxy rejection, and mapping change/removal.

A deliberately invalid certificate loads only under the matching insecure
mapping. Normal-mode, ordinary-host, and HSTS cases produce fresh bad-certificate
handshake failures. In unchanged insecure mode, three sequential connections
report `sessionReused = false, true, true`; switching to normal mode rejects
the bad certificate again. The toolbar DOM checks prove the normal label,
explicit insecure warning, and hidden indicator for an ordinary host.

The snapshot tests prove a socket created before activation cannot acquire an
insecure snapshot from a later preference edit. Authorization tests reject
empty, strict, removed, changed-address and mismatched-peer contexts. Session
keys isolate mode/address changes. A complete timed late-handshake race has not
been reproduced; the review and immutable-context/key tests establish the
intended protection without claiming instantaneous cross-process revocation.

Optional Human/owner check: extract the archive, start its portable launcher,
set the documented preference and inspect the label/layout in a GUI session.
No human interaction is required for integration after the required automated
checks above. The chrome DOM and visible label bounds are checked; interactive GUI
appearance has not been inspected in a human session.

## Files and purpose

- `netwerk/base/HostOverride.{h,cpp}` and `StaticPrefList.yaml`: shared strict
  parser and default-empty profile preference.
- `nsHostResolver.{h,cpp}`: uncached synthetic address records before ordinary
  DNS/TRR/cache dispatch, using the existing external-resolution transport path.
- HTTP channel, connection-info/manager/entry/handler and `AlternateServices`:
  prevent alternate routing/proxies/coalescing, isolate connection identity and
  invalidate network/TLS state on edits.
- NSS socket control, certificate verification and socket-process IPC: immutable
  context and session-key partitioning, exact-peer scoped acceptance after
  normal verification and existing policy guards; no stored cert exceptions.
- DNS service interface/implementations and browser URL bar files: authoritative
  configuration getter and selected-tab normal/insecure indicator.
- Networking xpcshell, TLS GTests and `cambrian/tests/`: repeatable regression and
  real-browser protocol/security evidence.
- `cambrian/docs/`, README, verification mozconfig and packaging helper:
  investigation, configuration, limitations, reproducible checks and bundled
  documentation/fixture.

IPv4, exact ASCII hostnames, all ports and direct desktop Linux connections are
the initial scope. HTTP/3, Alt-Svc, HTTPS/SVCB routing, proxies and WebTransport
cannot bypass a mapping. Pinned-certificate mode and a management page remain
future work. Response-cache contents are retained; use a cache-bypassing reload.

## SOCKS follow-up (2026-11-04)

The unchanged `master` revision `95fe0d05ee1edeac968b659a2bcf825fe3e00b9d`
built successfully in a fresh Ubuntu 24.04 x86_64 build environment, with
Clang 22.1.8, Rust 1.99.1 and the existing test-enabled mozconfig. The original
browser matrix passed all 33 checks with the socket process enabled. A SOCKS5
proxy-DNS reproduction failed at mapped navigation; the HTTP log explicitly
recorded `nsHttpChannel::BeginConnect refusing overridden proxied host`.

The no-system-changes bootstrap wrapper did not install Rust on the fresh
machine. Rust was provisioned separately without changing source; this is
tracked in [issue #3](https://github.com/oscmp-cambrian/cambrian-firefox/issues/3).
The initial two-job build was intentionally stopped and resumed with four jobs.
The successful build log is `build-baseline-final.log`.

The follow-up permits SOCKS4/5, captures the mapped destination in the SOCKS
layer, and retains network-state origin attributes for mapped SOCKS connections
so the TLS override gate sees the same HSTS partition as header processing.
The first SOCKS matrix exposed that partition mismatch; the corrected matrix
passes with the normal proxy-partitioning preference set to its default false.
No global privacy or certificate setting was weakened to obtain these results.

| Required check (Agent) | Result | Evidence under `/workspace/firefox-build/logs/` |
| --- | --- | --- |
| Patched native build | Passed, zero compiler warnings | `build-socks-hsts.log` |
| Focused SOCKS5 proxy-DNS reproduction | Passed; numeric mapped destination, original Host, proxy source address | `fixed-socks-reproduction.json` |
| Direct browser matrix, socket process on/off | Passed, 33 checks each | `fixed-direct-on.json`, `fixed-direct-off.json` |
| SOCKS4/5 × local/proxy DNS × socket process on/off | Passed, 8 cases, 35 checks each | `fixed-socks*-dns-*.json` |
| SOCKS5 proxy DNS with IPv6 proxy listener and PAC selection | Passed, 2 cases, 35 checks each | `fixed-socks5-ipv6.json`, `fixed-socks5-pac.json` |
| DNS regression | Passed, 29 subtests | `fixed-native-dns.log` |
| Immutable TLS snapshot/session-key GTests | Passed, 2 tests | `fixed-native-snapshot.log` |
| Existing TLS session-resumption regression | Passed, 154 subtests | `fixed-native-session.log` |
| Existing private-browsing session-cache regression | Passed, 17 subtests | `fixed-native-pbm.log` |
| Native formatting | Passed, zero findings | `clang-format-hsts.log` |

All 416 browser assertions passed. Each report records the actual proxy
partitioning preference as false, `acceptInsecureCerts=false`, and the requested
socket-process mode. Successful mapped requests reached `127.0.0.2` through a
proxy forwarding from `127.0.0.3`, with numeric SOCKS destination requests.
Mapped hostname-resolution requests are rejected by the assertion while the
mapping is active. Stopping the proxy must fail the request without a direct
endpoint connection. HTTP/HTTPS/H2, WS/WSS, identity, cookies, CORS, strict and
insecure TLS, learned HSTS rejection, session resumption, mapping edits,
HTTP-proxy rejection and the indicator checks remain in the matrix.

`baseline-provenance.json`, `browser-matrix-summary.json` and
`native-tests-summary.json` retain the source baseline, implementation/fixture
hashes and command results. Initial failing matrix evidence is retained under
`initial-socks-matrix/`; the partition-enabled diagnostic is not acceptance
proof. The PR and portable bundle manifest identify the delivered source
revision. Reproduction commands are in `cambrian/tests/README.md`.

The portable package's fixture list now includes `socks_proxy.py` alongside the
browser harness and Node server, so the bundled tests retain their dependency.
Optional Human/owner verification remains a GUI check with an isolated profile;
no human interaction is required for integration after the automated checks.

The audit also confirmed and separately filed
[malformed-list DNS fallback (#4)](https://github.com/oscmp-cambrian/cambrian-firefox/issues/4)
and [DNS preprocessing precedence (#5)](https://github.com/oscmp-cambrian/cambrian-firefox/issues/5).
Their implementations are intentionally unchanged by the SOCKS fix.
