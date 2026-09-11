# Donut Proxy Provider Diagnostic Report

*Executed on: 2026-09-10 15:30:12 UTC*

## Diagnostic Summary Table

| Test | Proxy | Target | Success | HTTP | Time | Exit IP | Error |
|---|---|---|---|---:|---:|---|---|
| 1 | GeoNode Residential | example.com | YES | 200 | 2618 ms | `216.75.151.156` | `None` |
| 2 | GeoNode Residential | kroger.com | NO | N/A | 45281 ms | `82.40.107.135` | `Page load timed out after 45s` |
| 3 | DataImpulse Residential | kroger.com | NO | N/A | 45385 ms | `165.140.26.102` | `Page load timed out after 45s` |

---

## Test Event & Session Trace

### Test 1 — GeoNode Residential (example.com)
- **Donut Profile Identifier**: `donut-profile-diag-01`
- **Proxy Session ID**: `dnut01`
- **Proxy Exit IP**: `216.75.151.156`
- **Final URL**: `https://example.com/`
- **Recorded Bytes**: 1278 bytes
- **CDP Network Trace**: Response: 200 url=https://example.com/

### Test 2 — GeoNode Residential (kroger.com)
- **Donut Profile Identifier**: `donut-profile-diag-02`
- **Proxy Session ID**: `dnut02`
- **Proxy Exit IP**: `82.40.107.135`
- **Final URL**: `about:blank`
- **Recorded Bytes**: 436 bytes
- **CDP Network Trace**: LoadingFailed: net::ERR_ABORTED

### Test 3 — DataImpulse Residential (kroger.com)
- **Donut Profile Identifier**: `donut-profile-diag-03`
- **Proxy Session ID**: `dnut03`
- **Proxy Exit IP**: `165.140.26.102`
- **Final URL**: `about:blank`
- **Recorded Bytes**: 436 bytes
- **CDP Network Trace**: LoadingFailed: net::ERR_ABORTED


---

## Diagnosis

**"Kroger-specific blocking/compatibility of proxied browser traffic is likely."**
