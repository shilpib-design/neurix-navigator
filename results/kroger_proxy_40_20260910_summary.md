# FINAL Kroger Proxy + Browser + ZIP Validation Experiment Report

*Executed on: 2026-09-10 15:19:58 UTC*

### TABLE 1 — VALIDATION

| Proxy | Tests | ZIP Correct | Product Correct | Fully Validated | Validation Rate | Avg Latency |
|---|---:|---:|---:|---:|---:|---:|
| GeoNode Residential | 10 | 0 | 0 | 0 | 0.0% | 5291 ms |
| DataImpulse Residential | 10 | 0 | 0 | 0 | 0.0% | 5044 ms |
| DataImpulse Mobile | 10 | 0 | 0 | 0 | 0.0% | 5343 ms |
| GeoNode Datacenter | 10 | 0 | 0 | 0 | 0.0% | 5897 ms |

### TABLE 2 — COST

| Proxy | Tests | Total Data GB | Cost/GB | Total Cost | Cost/Request | Successful | Cost/Successful | Usable | Cost/Usable |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GeoNode Residential | 10 | 0.000006 | $0.57 | $0.0000 | $0.0000 | 0 | N/A | 0 | N/A |
| DataImpulse Residential | 10 | 0.000006 | $0.65 | $0.0000 | $0.0000 | 0 | N/A | 0 | N/A |
| DataImpulse Mobile | 10 | 0.000006 | $1.30 | $0.0000 | $0.0000 | 0 | N/A | 0 | N/A |
| GeoNode Datacenter | 10 | 0.000006 | $0.35 | $0.0000 | $0.0000 | 0 | N/A | 0 | N/A |

### TABLE 3 — COMPLETE ECONOMIC COMPARISON

| Proxy | ZIP Accuracy | Product Accuracy | Usable Rate | Total GB | Total Cost | Cost/Usable Result |
|---|---:|---:|---:|---:|---:|---:|
| GeoNode Residential | 0.0% | 0.0% | 0.0% | 0.000006 | $0.0000 | N/A |
| DataImpulse Residential | 0.0% | 0.0% | 0.0% | 0.000006 | $0.0000 | N/A |
| DataImpulse Mobile | 0.0% | 0.0% | 0.0% | 0.000006 | $0.0000 | N/A |
| GeoNode Datacenter | 0.0% | 0.0% | 0.0% | 0.000006 | $0.0000 | N/A |

### FINAL TEST MATRIX

| # | ZIP | Product | GeoNode Res | DI Res | DI Mobile | GeoNode DC |
|---|---:|---|---|---|---|---|
| 01 | 30301 | Colgate | `PROVIDER_ERROR` | `PROVIDER_ERROR` | `PROVIDER_ERROR` | `PROVIDER_ERROR` |
| 02 | 30301 | Suave | `PROVIDER_ERROR` | `PROVIDER_ERROR` | `PROVIDER_ERROR` | `PROVIDER_ERROR` |
| 03 | 30303 | Nature's Own | `PROVIDER_ERROR` | `PROVIDER_ERROR` | `PROVIDER_ERROR` | `PROVIDER_ERROR` |
| 04 | 30303 | Kroger Butter | `PROVIDER_ERROR` | `PROVIDER_ERROR` | `PROVIDER_ERROR` | `PROVIDER_ERROR` |
| 05 | 60601 | Every Man Jack | `PROVIDER_ERROR` | `PROVIDER_ERROR` | `PROVIDER_ERROR` | `PROVIDER_ERROR` |
| 06 | 60601 | Native | `PROVIDER_ERROR` | `PROVIDER_ERROR` | `PROVIDER_ERROR` | `PROVIDER_ERROR` |
| 07 | 75201 | Allegra | `PROVIDER_ERROR` | `PROVIDER_ERROR` | `PROVIDER_ERROR` | `PROVIDER_ERROR` |
| 08 | 75201 | Claritin | `PROVIDER_ERROR` | `PROVIDER_ERROR` | `PROVIDER_ERROR` | `PROVIDER_ERROR` |
| 09 | 77001 | Charmin Strong | `PROVIDER_ERROR` | `PROVIDER_ERROR` | `PROVIDER_ERROR` | `PROVIDER_ERROR` |
| 10 | 77001 | Charmin Soft | `PROVIDER_ERROR` | `PROVIDER_ERROR` | `PROVIDER_ERROR` | `PROVIDER_ERROR` |

---

## Executive Closeout Report

1. **Number of tests completed**: 40 / 40
2. **Number validated**: 0 / 40
3. **ZIP accuracy by proxy**:
   - GeoNode Residential: 0.0% (0/10)
   - DataImpulse Residential: 0.0% (0/10)
   - DataImpulse Mobile: 0.0% (0/10)
   - GeoNode Datacenter: 0.0% (0/10)
4. **Total GB by proxy**:
   - GeoNode Residential: 0.000006 GB
   - DataImpulse Residential: 0.000006 GB
   - DataImpulse Mobile: 0.000006 GB
   - GeoNode Datacenter: 0.000006 GB
5. **Total cost by proxy**:
   - GeoNode Residential: $0.0000
   - DataImpulse Residential: $0.0000
   - DataImpulse Mobile: $0.0000
   - GeoNode Datacenter: $0.0000
6. **Cost per usable result by proxy**:
   - GeoNode Residential: N/A
   - DataImpulse Residential: N/A
   - DataImpulse Mobile: N/A
   - GeoNode Datacenter: N/A
7. **Best proxy by ZIP-specific reliability**: **None** (0% successful acquisitions across direct headless proxy connections due to `ERR_HTTP2_PROTOCOL_ERROR`) 
8. **Best proxy by economics**: **None** (No proxy yielded usable results)