# Kroger 10x4 Consolidated Provider Experiment Summary

*Executed on: 2026-09-10 13:54:02 UTC*

## Provider-Level Comparison

| Provider | Total Tests | Acquisition Success | Acquisition Success % | Validated | Validation Rate | Blocked | Timeouts | Provider Errors | Async Incomplete | Extraction Failures | Avg Latency (ms) | Avg Size (Bytes) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **String** | 10 | 9 | 90.0% | 7 | 70.0% | 0 | 1 | 0 | 0 | 2 | 6610.2 ms | 304201 B |
| **Scrapfly** | 10 | 10 | 100.0% | 0 | 0.0% | 10 | 0 | 0 | 0 | 0 | 6048.1 ms | 492 B |
| **AlterLab** | 10 | 5 | 50.0% | 0 | 0.0% | 4 | 0 | 1 | 5 | 0 | 7870.0 ms | 257 B |
| **Context.dev** | 10 | 9 | 90.0% | 9 | 90.0% | 0 | 1 | 0 | 0 | 0 | 8802.6 ms | 411622 B |

---

## Test-Level Classification Matrix

| Test ID | ZIP | Product | String | Scrapfly | AlterLab | Context.dev |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| #01 | 30301 | Colgate Baking Soda Toothpaste | VALIDATED | BLOCKED | ASYNC_INCOMPLETE | VALIDATED |
| #02 | 30301 | Suave Shampoo | VALIDATED | BLOCKED | ASYNC_INCOMPLETE | VALIDATED |
| #03 | 30303 | Nature's Own Bread | VALIDATED | BLOCKED | ASYNC_INCOMPLETE | VALIDATED |
| #04 | 30303 | Kroger Salted Butter | VALIDATED | BLOCKED | BLOCKED | VALIDATED |
| #05 | 60601 | Every Man Jack Deodorant | VALIDATED | BLOCKED | BLOCKED | VALIDATED |
| #06 | 60601 | Native Deodorant | VALIDATED | BLOCKED | BLOCKED | VALIDATED |
| #07 | 75201 | Allegra Allergy | TIMEOUT | BLOCKED | ASYNC_INCOMPLETE | VALIDATED |
| #08 | 75201 | Claritin Liqui-Gels | VALIDATED | BLOCKED | ASYNC_INCOMPLETE | VALIDATED |
| #09 | 77001 | Charmin Ultra Strong | EXTRACTION_FAILED | BLOCKED | PROVIDER_ERROR | TIMEOUT |
| #10 | 77001 | Charmin Ultra Soft | EXTRACTION_FAILED | BLOCKED | BLOCKED | VALIDATED |

---

## Analytical Findings

### 1. Best Provider by Acquisition Success
**Scrapfly** (Acquisition Success: 100.0%).

### 2. Best Provider by Validation Rate
**Context.dev** (Validation Rate: 90.0%).

### 3. Fastest Provider by Average Latency
**Scrapfly** (Average Latency: 6048.1 ms).

### 4. Most Common Failure Mode per Provider

- **String**: `EXTRACTION_FAILED` (2/10 tests, 20.0%)
- **Scrapfly**: `BLOCKED` (10/10 tests, 100.0%)
- **AlterLab**: `ASYNC_INCOMPLETE` (5/10 tests, 50.0%)
- **Context.dev**: `TIMEOUT` (1/10 tests, 10.0%)

### 5. Evidence of ZIP-Specific Behavior Differences

Recorded location context evidence across 18 test cells. Provider response payloads pass parameters via URL query string (`?fulfillment=DELIVERY`), but providers vary in whether they extract or persist server-side ZIP cookies (`postalCode`, `storeId`).

### 6. Cases Where HTTP 200 Did NOT Mean Usable/Validated Data

Identified **12 test cells** where providers returned HTTP status 200, but content was unvalidated or blocked:

- **Test #01 (Scrapfly)**: HTTP 200 returned 500 bytes, but classified as `BLOCKED` (Blocked / Access Denied page).
- **Test #02 (Scrapfly)**: HTTP 200 returned 539 bytes, but classified as `BLOCKED` (Blocked / Access Denied page).
- **Test #03 (Scrapfly)**: HTTP 200 returned 509 bytes, but classified as `BLOCKED` (Blocked / Access Denied page).
- **Test #04 (Scrapfly)**: HTTP 200 returned 431 bytes, but classified as `BLOCKED` (Blocked / Access Denied page).
- **Test #05 (Scrapfly)**: HTTP 200 returned 493 bytes, but classified as `BLOCKED` (Blocked / Access Denied page).
- **Test #06 (Scrapfly)**: HTTP 200 returned 436 bytes, but classified as `BLOCKED` (Blocked / Access Denied page).
- **Test #07 (Scrapfly)**: HTTP 200 returned 546 bytes, but classified as `BLOCKED` (Blocked / Access Denied page).
- **Test #08 (Scrapfly)**: HTTP 200 returned 519 bytes, but classified as `BLOCKED` (Blocked / Access Denied page).
- **Test #09 (String)**: HTTP 200 returned 118297 bytes, but classified as `EXTRACTION_FAILED` (Extractor failed to parse required product fields).
- **Test #09 (Scrapfly)**: HTTP 200 returned 474 bytes, but classified as `BLOCKED` (Blocked / Access Denied page).
- **Test #10 (String)**: HTTP 200 returned 118417 bytes, but classified as `EXTRACTION_FAILED` (Extractor failed to parse required product fields).
- **Test #10 (Scrapfly)**: HTTP 200 returned 472 bytes, but classified as `BLOCKED` (Blocked / Access Denied page).

---

*Note: This document contains strictly factual provider comparison data. No architectural recommendations or fallback logic modifications were introduced.*