# Neurix Navigator-01
## Final Technical & Product Report

---

## 1. Executive Summary

### Intent of Navigator-01
Neurix Navigator-01 was initiated to evaluate whether web data acquisition, extraction, and validation can be unified into an automated, deterministic system. The project set out to test whether commercial scraping vendors are necessary or whether direct Chrome DevTools Protocol (CDP) browser acquisition can serve as a robust, target-agnostic acquisition foundation for multi-retailer price and product intelligence.

### What Was Ultimately Proven
Navigator-01 successfully established that:
1. **Generic CDP Browser Acquisition Works Across Retailers**: A single, site-agnostic browser acquisition client ([browser/cdp.py](file:///Users/shilpibhawna/Documents/neurix-navigator-01/browser/cdp.py) & [browser/acquisition.py](file:///Users/shilpibhawna/Documents/neurix-navigator-01/browser/acquisition.py)) acquired raw rendered HTML for Kroger (US grocery), Amazon India (e-commerce), and Flipkart India (e-commerce) without any site-specific code in the browser layer.
2. **Third-Party Vendors Are Unnecessary for Primary Acquisition**: Direct CDP browser attachment achieved 100% extraction and validation success on tested targets without paying third-party scraping API vendor fees.
3. **Location Context Resolution Is Deterministic**: Kroger ZIP-level delivery location context (ZIP 30301) was successfully resolved down to delivery facility/store context headers and cookies.
4. **Data Acquisition, Extraction, and Validation Must Be Decoupled**: Evaluated vendor APIs demonstrated that HTTP 200 status codes do not guarantee usable data (e.g. Scrapfly returned HTTP 200 with 450 bytes of access-denied HTML on Kroger).
5. **Deterministic Strategy Scoring Works**: Historical telemetry observations can be recorded ([telemetry/](file:///Users/shilpibhawna/Documents/neurix-navigator-01/telemetry)) and scored ([scoring/](file:///Users/shilpibhawna/Documents/neurix-navigator-01/scoring)) based on validation rate, success rate, latency, and cost per validated result.

### Most Important Architectural Conclusion
**Acquisition, extraction, and validation must remain strictly decoupled.** Web scraping vendor APIs are merely interchangeable acquisition strategies within an orchestrator—not architecture owners. Business success is defined exclusively by validated, schema-compliant product data, not HTTP status codes or raw bytes.

### Most Important Product Conclusion
Neurix should evolve from a **"scraping vendor aggregator"** into a **"web data acquisition orchestrator"**. Product optimization must be driven by **Cost Per Validated Usable Result** rather than cost per HTTP request.

---

## 2. Original Hypothesis

The foundational thesis of Phase 0 was:

> *"Neurix automatically determines the best way to acquire, extract and validate web data for a given target."*

### How Navigator-01 Tested This Thesis
1. **Vendor Benchmarking (Phase 0/1)**: Evaluated 4 commercial scraping APIs (String, Scrapfly, AlterLab, Context.dev) across 3 targets to assess accuracy, latency, and cost.
2. **Generic CDP Browser Acquisition (Phases 2–5)**: Built a site-agnostic CDP browser engine and verified its performance on Kroger, Amazon India, and Flipkart India.
3. **Target Extraction & Validation (Phase 6)**: Created a generic extraction registry and validation engine enforcing business schema completeness.
4. **Telemetry & Outcome Tracking (Phase 7)**: Built an offline `AcquisitionObservation` telemetry system to persist attempt metrics and business outcomes to JSONL storage.
5. **Deterministic Strategy Scoring (Phase 8)**: Built a scoring engine that ranks acquisition strategies per target using historical telemetry, sample-size confidence scaling, and normalized cost/latency metrics.

---

## 3. Scope and Boundaries

### What Navigator-01 Includes
- Generic, target-agnostic CDP browser acquisition engine ([browser/cdp.py](file:///Users/shilpibhawna/Documents/neurix-navigator-01/browser/cdp.py))
- Kroger ZIP-level location resolution module ([kroger/resolver.py](file:///Users/shilpibhawna/Documents/neurix-navigator-01/kroger/resolver.py))
- Retailer extractors for Kroger, Amazon India, and Flipkart India
- Deterministic Acquisition Orchestrator ([orchestrator/orchestrator.py](file:///Users/shilpibhawna/Documents/neurix-navigator-01/orchestrator/orchestrator.py))
- Telemetry recorder with JSONL persistence ([telemetry/recorder.py](file:///Users/shilpibhawna/Documents/neurix-navigator-01/telemetry/recorder.py))
- Deterministic Strategy Scorer with confidence scaling ([scoring/scorer.py](file:///Users/shilpibhawna/Documents/neurix-navigator-01/scoring/scorer.py))
- 35 unit tests and offline example scripts

### Intentionally Excluded Scope
- **AI/LLM/ML Routing**: No machine learning or LLM calls were implemented.
- **Autonomous Domain Investigation**: Domain reverse-engineering was performed manually during development.
- **Automatic Fallback Execution**: The orchestrator recommends strategies but executes deterministically using pre-configured strategies.
- **Production Concurrency**: Multi-threading, browser pooling, and distributed scaling were not implemented.
- **Anti-Bot / CAPTCHA Bypass**: Stealth plugins, proxy rotation, and CAPTCHA solving were explicitly excluded.

---

## 4. Final Architecture

```
Customer Request (Target, Parameters, Requirements)
       │
       ▼
AcquisitionOrchestrator
       │
       ├─────────────────────────────────────────┐
       ▼                                         ▼
BrowserCDPStrategy                       VendorAPIStrategy (Stub)
       │                                         │
       └────────────────────┬────────────────────┘
                            │
                            ▼
                    Raw Content (HTML)
                            │
                            ▼
                  TargetExtractorRegistry
                            │
                            ▼
                     TargetValidator
                            │
                            ▼
                 AcquisitionObservation
                            │
                            ▼
                      StrategyScorer
```

### Component Responsibilities & Separation of Concerns
1. **`AcquisitionRequest`**: Encapsulates target key, URL, parameters (e.g. ZIP, ASIN, UPC), and required schema fields.
2. **`AcquisitionOrchestrator`**: Routes requests through strategy selection, acquisition, extraction, and validation.
3. **`BaseAcquisitionStrategy`**: Strategy interface implemented by `BrowserCDPStrategy` and vendor stubs.
4. **`TargetExtractorRegistry`**: Decoupled registry mapping target identifiers (`kroger`, `amazon`, `flipkart`) to specialized parsing functions.
5. **`TargetValidator`**: Schema and evidence validator ensuring required business fields (`product_name`, `price`, `availability`) are present and non-empty.
6. **`AcquisitionObservation`**: Telemetry model recording performance metrics, costs, and final business outcome status (`VALIDATED`, `ACQUISITION_FAILED`, `EXTRACTION_FAILED`, `VALIDATION_FAILED`).
7. **`StrategyScorer`**: Deterministic scoring engine computing target-isolated strategy ranks based on historical observations.

---

## 5. Browser Acquisition Layer

The generic browser acquisition layer consists of two core files:
- [browser/cdp.py](file:///Users/shilpibhawna/Documents/neurix-navigator-01/browser/cdp.py) (`GenericCDPClient`)
- [browser/acquisition.py](file:///Users/shilpibhawna/Documents/neurix-navigator-01/browser/acquisition.py) (`CDPAcquisitionEngine`)

### Key Design Attributes
- **Target-Agnostic**: Contains zero retailer selectors, URL patterns, or site-specific rules. Accepts any valid HTTP/HTTPS URL.
- **CDP Attachment**: Connects to an existing browser instance using Playwright's `connect_over_cdp(endpoint_url)`.
- **Context & Page Reuse**: Utilizes active pages/contexts rather than launching new browser windows or opening unnecessary tabs.
- **Dynamic Port Discovery**: Auto-detects local CDP debugging ports from process arguments or debugging endpoints.
- **Readiness Wait**: Waits for DOM content load, network idle, and body element rendering before capturing full page HTML.

---

## 6. Donut Browser Findings

### Experimental Setup & Local Discovery
During Phase 2, a pre-existing Donut Browser profile (`Kroger-Test-30301`) was running locally. Process inspection revealed:
- Donut local REST endpoints (`/run`, `/open-url`) returned `HTTP 402 Payment Required` (Pro paid feature).
- Direct process inspection (`ps aux | grep Donut`) revealed an active Chrome DevTools Protocol remote debugging port (e.g., CDP port 9222/50212).

### Technical Workaround
Neurix connected directly to the exposed CDP HTTP endpoint (`http://127.0.0.1:<port>/json/version`) to discover the `webSocketDebuggerUrl`, bypassing paid Donut REST endpoints completely using standard Playwright `connect_over_cdp`.

### Strategic Product Distinction
**Donut Browser is merely an execution environment for development—it is NOT a required Neurix product dependency.** Neurix's `GenericCDPClient` attaches to any standard CDP-compliant browser (headless Chrome, Chromium, Playwright instances, Remote CDP containers).

---

## 7. Kroger ZIP-Level Investigation

### Location Context Hierarchy
Investigation of Kroger's web architecture established that pricing and availability are strictly dependent on location context:

```
ZIP Code (e.g., 30301)
   │
   ▼
Kroger Modality Resolution Endpoint (/api/v1/user/modality)
   │
   ▼
Geographic Coordinates (Lat/Lng) & Delivery Facility ID
   │
   ▼
Session Cookies & Headers (Store ID, Modality = DELIVERY)
   │
   ▼
Location-Specific Product Listing & Price ($1.49 at 30301 vs Unavailable/Different Price)
```

### Key Findings from HAR Analysis
- **ZIP-Only Resolution**: Kroger maps ZIP codes (e.g. 30301 Atlanta vs 30305 Buckhead) to specific fulfillment facility IDs and primary store numbers.
- **Context Injection**: Location context is passed via headers (`x-preference-store-id`, `x-fulfillment-mode`) and session cookies (`rutile`, `krogerSessionId`).
- **Dynamic Payload Mutation**: Querying product APIs or rendering product pages without valid location context defaults to national fallback state or displays out-of-stock messages.

---

## 8. Vendor Acquisition Experiment

In Phase 0/1, 12 acquisition requests were conducted across 4 commercial vendors and 3 targets.

### Vendor Performance Matrix

| Target | Provider | Status Code | Elapsed (ms) | Size (Bytes) | Usable Data Result |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Flipkart** | String | 200 | 4,783 ms | 1,533,645 | **YES** (Valid HTML & JSON-LD) |
| **Flipkart** | Scrapfly | 200 | 5,141 ms | 1,537,659 | **YES** (Valid HTML) |
| **Flipkart** | AlterLab | Timed Out | 30,280 ms | 0 | **NO** (Request Timeout) |
| **Flipkart** | Context.dev | 200 | 5,932 ms | 868,715 | **YES** (Valid HTML) |
| **Amazon India** | String | 200 | 4,682 ms | 2,221,978 | **YES** (Valid HTML) |
| **Amazon India** | Scrapfly | 200 | 7,050 ms | 2,218,964 | **YES** (Valid HTML) |
| **Amazon India** | AlterLab | 202 | 588 ms | 262 | **NO** (Async Job Created, Unpolled) |
| **Amazon India** | Context.dev | 200 | 6,799 ms | 2,100,354 | **YES** (Valid HTML) |
| **Kroger** | String | 200 | 4,500 ms | 478,912 | **YES** (Valid HTML) |
| **Kroger** | Scrapfly | 200 | 2,318 ms | 450 | **NO** (Access Denied / Anti-bot Block) |
| **Kroger** | AlterLab | 202 | 8,683 ms | 248 | **NO** (Async Job Created, Unpolled) |
| **Kroger** | Context.dev | 200 | 5,782 ms | 595,202 | **YES** (Valid HTML) |

### Important Architectural Observations
1. **HTTP 200 $\neq$ Usable Data**: Scrapfly returned HTTP 200 for Kroger, but the payload was a 450-byte anti-bot block page.
2. **Asynchronous API Differences**: AlterLab returned HTTP 202 Accepted with a job ID. This is an asynchronous polling API, not a synchronous page acquisition engine, making raw HTML comparisons invalid without polling.

---

## 9. Cross-Site Browser Acquisition Results

Direct CDP browser acquisition was executed against all three targets using [browser/cdp.py](file:///Users/shilpibhawna/Documents/neurix-navigator-01/browser/cdp.py).

### Real CDP Acquisition Performance

| Target | URL | Latency | Payload Size | Saved HTML Path | Extracted Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Kroger** | `https://www.kroger.com/p/snickers-singles.../0004000042431` | 2,676 ms | 975,764 B | [results/donut_kroger_cdp_20260910_182522.html](file:///Users/shilpibhawna/Documents/neurix-navigator-01/results/donut_kroger_cdp_20260910_182522.html) | Snickers Singles 1.86 oz<br>UPC: 0004000042431<br>Price: $1.49<br>ZIP: 30301 / Delivery |
| **Amazon India** | `https://www.amazon.in/dp/B078Y2PJL4` | 5,387 ms | 614,022 B | [results/donut_amazon_cdp_20260910_183943.html](file:///Users/shilpibhawna/Documents/neurix-navigator-01/results/donut_amazon_cdp_20260910_183943.html) | SanDisk Ultra MicroSDHC 32GB<br>ASIN: B078Y2PJL4<br>Price: ₹369 |
| **Flipkart India** | `https://www.flipkart.com/panasonic.../p/itmffgx6p6c2wgda` | 3,969 ms | 344,400 B | [results/donut_flipkart_cdp_20260910_184126.html](file:///Users/shilpibhawna/Documents/neurix-navigator-01/results/donut_flipkart_cdp_20260910_184126.html) | Panasonic H-HSA35100E Lens<br>ID: `itmffgx6p6c2wgda`<br>Price: ₹114,990 |

---

## 10. Extraction and Validation Philosophy

### Core Principles
1. **Raw Content Preservation**: All acquired HTML is saved to disk prior to parsing for full replayability and auditing.
2. **Local Extraction**: Extraction occurs locally via decoupled target modules ([kroger/product.py](file:///Users/shilpibhawna/Documents/neurix-navigator-01/kroger/product.py), [amazon/product.py](file:///Users/shilpibhawna/Documents/neurix-navigator-01/amazon/product.py), [flipkart/product.py](file:///Users/shilpibhawna/Documents/neurix-navigator-01/flipkart/product.py)) using JSON-LD, DOM structures, and embedded scripts (`window.__INITIAL_STATE__`).
3. **Structural Validation**: `TargetValidator` verifies mandatory business fields (`product_name`, `price`, `availability`) rather than relying on HTTP response codes or non-zero byte counts.

---

## 11. Acquisition Orchestrator

The deterministic orchestrator ([orchestrator/orchestrator.py](file:///Users/shilpibhawna/Documents/neurix-navigator-01/orchestrator/orchestrator.py)) executes a strict sequential pipeline:

$$\text{Strategy Selection} \longrightarrow \text{Acquisition} \longrightarrow \text{Target Extraction} \longrightarrow \text{Validation}$$

### Explicit Orchestration Statuses
- `SUCCESS`: Acquisition, extraction, and validation all succeeded.
- `VALIDATION_FAILED`: Extracted data was incomplete or missing required business fields.
- `EXTRACTION_FAILED`: Extractor returned empty or threw an unhandled exception.
- `ACQUISITION_FAILED`: Browser or API strategy failed to retrieve content.
- `NO_EXTRACTOR`: Target key has no registered extractor in `TargetExtractorRegistry`.
- `NO_STRATEGY`: No available strategy configured for request.

---

## 12. Telemetry / Outcome Model

### Structure & Storage
- Implemented in [telemetry/models.py](file:///Users/shilpibhawna/Documents/neurix-navigator-01/telemetry/models.py) and persisted to JSONL format via `TelemetryRecorder` ([telemetry/recorder.py](file:///Users/shilpibhawna/Documents/neurix-navigator-01/telemetry/recorder.py)).
- Raw HTML is referenced by file path rather than embedded in telemetry records to keep log file sizes minimal.

### Primary Outcome Statuses
- `VALIDATED`
- `VALIDATION_FAILED`
- `EXTRACTION_FAILED`
- `ACQUISITION_FAILED`

### Key Derived Metrics
- $\text{Success Rate} = \frac{\text{successful\_acquisitions}}{\text{sample\_size}}$
- $\text{Validation Rate} = \frac{\text{validated\_results}}{\text{sample\_size}}$
- $\text{Average Latency} = \frac{\sum \text{elapsed\_ms}}{\text{sample\_size}}$
- $\text{Cost Per Validated Result} = \frac{\sum \text{acquisition\_cost}}{\text{validated\_results}}$

---

## 13. Deterministic Strategy Scoring

Implemented in [scoring/scorer.py](file:///Users/shilpibhawna/Documents/neurix-navigator-01/scoring/scorer.py).

### Scoring & Confidence Formula

$$\text{raw\_score} = 0.50 \times \text{validation\_rate} + 0.20 \times \text{success\_rate} + 0.15 \times \text{latency\_score} + 0.15 \times \text{cost\_score}$$

$$\text{confidence} = \min\left(1.0, \frac{\text{sample\_size}}{10}\right)$$

$$\text{final\_score} = \text{raw\_score} \times \text{confidence}$$

### Key Features
- **Target Isolation**: Observations are grouped strictly by `(target, acquisition_method)`. Kroger metrics never contaminate Amazon or Flipkart scores.
- **Cold Start (`UNSEEN`)**: Strategies with zero observations receive `status = "UNSEEN"`, `confidence = 0.0`, `final_score = 0.0`, but remain listed in rankings.
- **Non-blocking Recommendation**: `orchestrator.recommend_strategy()` provides strategy recommendations without altering current execution logic.

---

## 14. Test Coverage Summary

The project maintains **35 unit tests** in [tests/](file:///Users/shilpibhawna/Documents/neurix-navigator-01/tests):

1. **`tests/test_orchestrator.py`** (10 tests):
   - Strategy selection when available
   - `NO_STRATEGY`, `NO_EXTRACTOR`, `ACQUISITION_FAILED`, `EXTRACTION_FAILED`, `VALIDATION_FAILED` status generation
   - Successful mocked flow execution
   - Selector isolation and offline execution verification

2. **`tests/test_telemetry.py`** (11 tests):
   - Observation creation for successful/failed acquisitions
   - Cost metrics calculation and zero-cost browser tracking
   - Cost per validated result denominator isolation
   - JSONL file persistence and path-based HTML reference verification

3. **`tests/test_scoring.py`** (14 tests):
   - Scenarios A through N: Target grouping, validation rate, success rate, latency normalization, cost normalization, confidence scaling, final score calculation, strategy ranking, `UNSEEN` handling, target isolation, zero-cost handling, mocked vendor cost, network isolation, and non-execution verification.

---

## 15. What Navigator-01 PROVED

1. **Generic CDP Acquisition Works**: Direct CDP browser attachment can acquire dynamic rendered HTML across diverse global web retailers without site-specific code in the browser engine.
2. **Elimination of Vendor Dependence**: Commercial scraping vendors are not required for primary data acquisition on tested targets.
3. **Location Context Control**: ZIP-level delivery context for location-sensitive sites like Kroger can be resolved deterministically.
4. **Architectural Decoupling**: Acquisition, target extraction, and validation can be cleanly separated into distinct, testable modules.
5. **Telemetry & Strategy Scoring**: Historical acquisition attempts can be recorded, evaluated, and ranked using deterministic multi-criteria scoring.

---

## 16. What Navigator-01 DID NOT PROVE

1. **Production Concurrency & Fleet Reliability**: Did not test concurrent multi-threaded execution or multi-instance browser fleet management.
2. **Universal CDP Applicability**: Did not prove CDP attachment works on anti-bot systems that detect and block Chrome DevTools Protocol automation.
3. **Autonomous Domain Investigation**: Did not prove automated discovery of selectors, APIs, or location mechanisms for unstudied domains.
4. **AI-Driven Self-Healing**: Did not implement or prove AI/LLM routing or automated DOM selector repair.
5. **Long-Term Statistical Economics**: Did not collect multi-thousand request datasets to establish long-term vendor vs browser cost ratios.

---

## 17. Production Gaps

Before deploying Navigator-01 to production, the following infrastructure gaps must be addressed:
- **Browser Fleet Management**: Lifecycle management, container pooling, memory cleanup, and process sandboxing.
- **Session & IP Isolation**: Residential proxy integration and anti-bot fingerprint masking.
- **Distributed Concurrency**: Async worker queues (e.g. Celery, Temporal) and rate limiting per target domain.
- **Persistent Telemetry DB**: Migrating local JSONL files to a relational or document database (e.g., PostgreSQL, Firestore).
- **Failure Recovery & Retries**: Automated fallback strategies when primary CDP acquisition is blocked.
- **Legal & Compliance**: Audit logging for target `robots.txt` compliance and site terms of service.

---

## 18. Product Implication for Neurix

Navigator-01 demonstrates a fundamental product pivot:

$$\text{From: "Scraping Vendor Aggregator"} \longrightarrow \text{To: "Web Data Acquisition Orchestrator"}$$

### Key Strategic Takeaways
- **Vendor Independence**: Acquisition engines (CDP, vendor APIs, headless browsers) are interchangeable plugins.
- **Ownership of Validation**: Neurix owns extraction quality and schema validation.
- **Cost Efficiency**: Success is measured by **Cost Per Validated Usable Result**, driving requests toward zero-cost CDP browser strategies whenever viable.

---

## 19. Future Product — Domain Investigation Engine

*(Note: Explicitly defined as a separate future component, NOT part of Navigator-01)*

The **Domain Investigation Engine** will be an autonomous system that automates the onboarding of new web targets:

```
Inputs: Target URL, Sample Products, Required Schema, Target Location/ZIP
                           │
                           ▼
             Domain Investigation Engine
   (Automated Reverse Engineering & Inspection)
                           │
                           ▼
Outputs: Location Mechanism Map, Selected Acquisition Strategy,
         Generated Extractor, Validation Rules, Executable Playbook
```

---

## 20. Recommended Neurix Roadmap

```
Phase 1: Navigator-01 Core Framework (COMPLETED)
   ├── Generic CDP Browser Acquisition
   ├── Target Extractor Registry & Validation Engine
   ├── Telemetry Recorder & JSONL Persistence
   └── Deterministic Strategy Scorer

Phase 2: Production Hardening (FUTURE)
   ├── Browser Fleet & Proxy Management
   ├── Async Worker Queue & Concurrency
   └── Centralized Telemetry Storage

Phase 3: Domain Investigation Engine (FUTURE)
   ├── Autonomous Target Inspection
   ├── Automated Location Resolver Discovery
   └── Self-Healing Extractor Generation
```

---

## 21. Final Conclusion

Navigator-01 successfully achieved its core experimental objectives.

- **Strongest Technical Proof**: Direct CDP browser acquisition cleanly acquired complex dynamic targets (Kroger, Amazon India, Flipkart India) with zero site-specific logic in the browser client.
- **Strongest Product Insight**: Decoupling acquisition from validation and optimizing for **Cost Per Validated Result** eliminates vendor lock-in.
- **Primary Remaining Uncertainty**: Long-term resilience of unmasked CDP browser connections against advanced anti-bot systems at production scale.

---

## Appendix A — Project Directory Structure

```
neurix-navigator-01/
├── amazon/
│   ├── __init__.py
│   └── product.py
├── browser/
│   ├── __init__.py
│   ├── acquisition.py
│   └── cdp.py
├── docs/
│   └── NAVIGATOR-01-FINAL-REPORT.md
├── examples/
│   ├── orchestrator_example.py
│   ├── scoring_example.py
│   └── telemetry_example.py
├── flipkart/
│   ├── __init__.py
│   └── product.py
├── kroger/
│   ├── __init__.py
│   ├── acquisition.py
│   ├── cdp_client.py
│   ├── product.py
│   └── resolver.py
├── orchestrator/
│   ├── __init__.py
│   ├── models.py
│   ├── orchestrator.py
│   └── strategies.py
├── results/
│   ├── donut_amazon_cdp_20260910_183943.html
│   ├── donut_flipkart_cdp_20260910_184126.html
│   ├── donut_kroger_cdp_20260910_182522.html
│   └── summary_20260910_084120.json
├── scoring/
│   ├── __init__.py
│   ├── models.py
│   └── scorer.py
├── telemetry/
│   ├── __init__.py
│   ├── models.py
│   └── recorder.py
└── tests/
    ├── test_orchestrator.py
    ├── test_scoring.py
    └── test_telemetry.py
```

---

## Appendix B — Key Experimental Results

### Cross-Site CDP Acquisition Summary

| Target | Latency (ms) | Raw HTML Size (Bytes) | Extracted Product | Extracted Price | Validation Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Kroger** | 2,676 ms | 975,764 B | Snickers Singles 1.86 oz | $1.49 | `VALIDATED` |
| **Amazon India** | 5,387 ms | 614,022 B | SanDisk Ultra MicroSDHC 32GB | ₹369 | `VALIDATED` |
| **Flipkart India**| 3,969 ms | 344,400 B | Panasonic H-HSA35100E Lens | ₹114,990 | `VALIDATED` |

---

## Appendix C — Important Design Principles

1. **$\text{HTTP 200} \neq \text{Usable Result}$**: Response codes do not guarantee non-blocked or complete content.
2. **$\text{Field Presence} \neq \text{Meaningful Data}$**: Null or empty strings do not satisfy validation requirements.
3. **$\text{Acquisition} \neq \text{Extraction} \neq \text{Validation}$**: Keep network fetch, data parsing, and business verification completely independent.
4. **Vendors Are Strategy Plugins**: Third-party scraping services should be managed as interchangeable strategies within an orchestrator.
5. **Replayable Raw Artifacts**: Always store original HTML/JSON payloads to allow offline re-extraction and testing.
6. **Target Logic Belongs in Extractors**: Generic browser and orchestrator code must remain 100% retailer-agnostic.
7. **Cost Per Validated Result Is Key**: Measure operational cost against validated outcomes rather than total outbound requests.
8. **Evidence-Based Strategy Recommendation**: Use historical telemetry observations and confidence scaling to rank strategies.
9. **Deterministic First, AI Second**: Rely on explicit deterministic rules for orchestration; introduce AI only where deterministic rules fail.
