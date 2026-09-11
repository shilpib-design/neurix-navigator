# Kroger 10x4 Forensic ZIP & Product Analysis Report

*Forensic inspection of all 40 existing test cells from `results/kroger_10x4_20260910.jsonl`*

## A. 40-Cell Detailed Matrix

| Test ID | ZIP | Provider | ZIP Status | Product Status | Validation | Evidence / Notes |
| :---: | :---: | :--- | :---: | :---: | :---: | :--- |
| #01 | 30301 | **String** | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | SUCCESS | Detected postalCode '61081' in payload (requested '30301') |
| #01 | 30301 | **Scrapfly** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #01 | 30301 | **AlterLab** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #01 | 30301 | **Context.dev** | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | SUCCESS | Detected postalCode '76049' in payload (requested '30301') |
| #02 | 30301 | **String** | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | SUCCESS | Detected postalCode '61081' in payload (requested '30301') |
| #02 | 30301 | **Scrapfly** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #02 | 30301 | **AlterLab** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #02 | 30301 | **Context.dev** | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | SUCCESS | Detected postalCode '23072' in payload (requested '30301') |
| #03 | 30303 | **String** | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | SUCCESS | Detected postalCode '61081' in payload (requested '30303') |
| #03 | 30303 | **Scrapfly** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #03 | 30303 | **AlterLab** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #03 | 30303 | **Context.dev** | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | SUCCESS | Detected postalCode '76049' in payload (requested '30303') |
| #04 | 30303 | **String** | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | SUCCESS | Detected postalCode '61081' in payload (requested '30303') |
| #04 | 30303 | **Scrapfly** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #04 | 30303 | **AlterLab** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #04 | 30303 | **Context.dev** | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | SUCCESS | Detected postalCode '23072' in payload (requested '30303') |
| #05 | 60601 | **String** | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | SUCCESS | Detected postalCode '61081' in payload (requested '60601') |
| #05 | 60601 | **Scrapfly** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #05 | 60601 | **AlterLab** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #05 | 60601 | **Context.dev** | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | SUCCESS | Detected postalCode '76049' in payload (requested '60601') |
| #06 | 60601 | **String** | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | SUCCESS | Detected postalCode '61081' in payload (requested '60601') |
| #06 | 60601 | **Scrapfly** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #06 | 60601 | **AlterLab** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #06 | 60601 | **Context.dev** | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | SUCCESS | Detected postalCode '76049' in payload (requested '60601') |
| #07 | 75201 | **String** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #07 | 75201 | **Scrapfly** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #07 | 75201 | **AlterLab** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #07 | 75201 | **Context.dev** | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | SUCCESS | Detected postalCode '76049' in payload (requested '75201') |
| #08 | 75201 | **String** | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | SUCCESS | Detected postalCode '36830' in payload (requested '75201') |
| #08 | 75201 | **Scrapfly** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #08 | 75201 | **AlterLab** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #08 | 75201 | **Context.dev** | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | SUCCESS | Detected postalCode '76049' in payload (requested '75201') |
| #09 | 77001 | **String** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | Fulfillment mode 'DELIVERY' present in payload |
| #09 | 77001 | **Scrapfly** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #09 | 77001 | **AlterLab** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #09 | 77001 | **Context.dev** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #10 | 77001 | **String** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | Fulfillment mode 'DELIVERY' present in payload |
| #10 | 77001 | **Scrapfly** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #10 | 77001 | **AlterLab** | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | FAILED | No postalCode or location evidence present in response payload |
| #10 | 77001 | **Context.dev** | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | SUCCESS | Detected postalCode '76049' in payload (requested '77001') |

---

## B. Provider Summary

| Provider | Tests | ZIP Confirmed | ZIP Mismatched | ZIP Unverified | Product Confirmed | Product Mismatch | Product Unverified | Validated | Validation Rate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **String** | 10 | 0 | 7 | 3 | 7 | 0 | 3 | 7 | 70.0% |
| **Scrapfly** | 10 | 0 | 0 | 10 | 0 | 0 | 10 | 0 | 0.0% |
| **AlterLab** | 10 | 0 | 0 | 10 | 0 | 0 | 10 | 0 | 0.0% |
| **Context.dev** | 10 | 0 | 9 | 1 | 9 | 0 | 1 | 9 | 90.0% |

---

## C. ZIP-Level Summary

### Target ZIP: `30301`

| Test ID | Provider | Detected ZIP | ZIP Status | Product Status | Result Classification |
| :---: | :--- | :---: | :---: | :---: | :--- |
| #01 | String | `61081` | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | `VALIDATED` |
| #01 | Scrapfly | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `BLOCKED` |
| #01 | AlterLab | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `ASYNC_INCOMPLETE` |
| #01 | Context.dev | `76049` | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | `VALIDATED` |
| #02 | String | `61081` | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | `VALIDATED` |
| #02 | Scrapfly | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `BLOCKED` |
| #02 | AlterLab | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `ASYNC_INCOMPLETE` |
| #02 | Context.dev | `23072` | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | `VALIDATED` |

### Target ZIP: `30303`

| Test ID | Provider | Detected ZIP | ZIP Status | Product Status | Result Classification |
| :---: | :--- | :---: | :---: | :---: | :--- |
| #03 | String | `61081` | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | `VALIDATED` |
| #03 | Scrapfly | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `BLOCKED` |
| #03 | AlterLab | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `ASYNC_INCOMPLETE` |
| #03 | Context.dev | `76049` | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | `VALIDATED` |
| #04 | String | `61081` | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | `VALIDATED` |
| #04 | Scrapfly | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `BLOCKED` |
| #04 | AlterLab | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `BLOCKED` |
| #04 | Context.dev | `23072` | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | `VALIDATED` |

### Target ZIP: `60601`

| Test ID | Provider | Detected ZIP | ZIP Status | Product Status | Result Classification |
| :---: | :--- | :---: | :---: | :---: | :--- |
| #05 | String | `61081` | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | `VALIDATED` |
| #05 | Scrapfly | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `BLOCKED` |
| #05 | AlterLab | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `BLOCKED` |
| #05 | Context.dev | `76049` | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | `VALIDATED` |
| #06 | String | `61081` | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | `VALIDATED` |
| #06 | Scrapfly | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `BLOCKED` |
| #06 | AlterLab | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `BLOCKED` |
| #06 | Context.dev | `76049` | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | `VALIDATED` |

### Target ZIP: `75201`

| Test ID | Provider | Detected ZIP | ZIP Status | Product Status | Result Classification |
| :---: | :--- | :---: | :---: | :---: | :--- |
| #07 | String | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `TIMEOUT` |
| #07 | Scrapfly | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `BLOCKED` |
| #07 | AlterLab | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `ASYNC_INCOMPLETE` |
| #07 | Context.dev | `76049` | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | `VALIDATED` |
| #08 | String | `36830` | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | `VALIDATED` |
| #08 | Scrapfly | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `BLOCKED` |
| #08 | AlterLab | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `ASYNC_INCOMPLETE` |
| #08 | Context.dev | `76049` | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | `VALIDATED` |

### Target ZIP: `77001`

| Test ID | Provider | Detected ZIP | ZIP Status | Product Status | Result Classification |
| :---: | :--- | :---: | :---: | :---: | :--- |
| #09 | String | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `EXTRACTION_FAILED` |
| #09 | Scrapfly | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `BLOCKED` |
| #09 | AlterLab | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `PROVIDER_ERROR` |
| #09 | Context.dev | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `TIMEOUT` |
| #10 | String | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `EXTRACTION_FAILED` |
| #10 | Scrapfly | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `BLOCKED` |
| #10 | AlterLab | `N/A` | `ZIP_UNVERIFIED` | `PRODUCT_UNVERIFIED` | `BLOCKED` |
| #10 | Context.dev | `76049` | `ZIP_MISMATCH` | `PRODUCT_CONFIRMED` | `VALIDATED` |


---

## D. Product-Level Summary

| Test ID | Product Name | String | Scrapfly | AlterLab | Context.dev |
| :---: | :--- | :---: | :---: | :---: | :---: |
| #01 | Colgate Baking Soda Toothpaste | PRODUCT_CONFIRMED / ZIP_MISMATCH | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_CONFIRMED / ZIP_MISMATCH |
| #02 | Suave Shampoo | PRODUCT_CONFIRMED / ZIP_MISMATCH | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_CONFIRMED / ZIP_MISMATCH |
| #03 | Nature's Own Bread | PRODUCT_CONFIRMED / ZIP_MISMATCH | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_CONFIRMED / ZIP_MISMATCH |
| #04 | Kroger Salted Butter | PRODUCT_CONFIRMED / ZIP_MISMATCH | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_CONFIRMED / ZIP_MISMATCH |
| #05 | Every Man Jack Deodorant | PRODUCT_CONFIRMED / ZIP_MISMATCH | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_CONFIRMED / ZIP_MISMATCH |
| #06 | Native Deodorant | PRODUCT_CONFIRMED / ZIP_MISMATCH | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_CONFIRMED / ZIP_MISMATCH |
| #07 | Allegra Allergy | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_CONFIRMED / ZIP_MISMATCH |
| #08 | Claritin Liqui-Gels | PRODUCT_CONFIRMED / ZIP_MISMATCH | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_CONFIRMED / ZIP_MISMATCH |
| #09 | Charmin Ultra Strong | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED |
| #10 | Charmin Ultra Soft | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_UNVERIFIED / ZIP_UNVERIFIED | PRODUCT_CONFIRMED / ZIP_MISMATCH |

---

## E. Critical Findings

### 1. Is Context.dev's 9/10 validation rate also 9/10 ZIP-correct?
**NO.** Context.dev achieved a 9/10 schema validation rate, but **0 out of 10 results were ZIP-correct** (`ZIP_CONFIRMED` = 0). Every single acquired result returned a mismatched default proxy location (postalCode `76049` or `23072`) rather than the requested target ZIP code (`30301`, `30303`, `60601`, `75201`, `77001`).

### 2. How many Context.dev results have explicit requested-ZIP evidence?
**0 (Zero).** None of the Context.dev response payloads contained explicit server-side evidence matching the requested target ZIP code.

### 3. How many Context.dev results are ZIP-unverified vs ZIP-mismatched?
- **ZIP_UNVERIFIED**: **1** (Test #09 timed out with 0 response bytes).
- **ZIP_MISMATCH**: **9** (9/10 tests acquired product HTML containing explicit mismatched postalCodes `76049` Granbury TX or `23072` Gloucester VA).

### 4. Did any provider return a product successfully but with a mismatched ZIP?
**YES.** All **16 validated product acquisitions** across String (7 tests) and Context.dev (9 tests) returned correct product details (matching description, brand, and UPC), but **100% of them returned a MISMATCHED ZIP**.

- **String**: Returned `61081` (Sterling, IL) for tests 1-6 or `36830` (Auburn, AL) for test 8 instead of requested ZIPs (`30301`, `30303`, `60601`, `75201`).
- **Context.dev**: Returned `76049` (Granbury, TX) or `23072` (Gloucester, VA) for all acquired tests instead of requested ZIPs.

### 5. Did any HTTP 200 result contain blocked/non-product content?
**YES.** Identified **12 test cells** returning HTTP status 200 with unusable content:
- **Scrapfly**: All 10/10 requests returned HTTP status 200 containing ~430-540 byte Akamai access-denied block pages (`BLOCKED`).
- **String**: 2/10 requests (Tests #09 & #10) returned HTTP status 200 with ~118 KB payloads containing unrendered page shells without populated product fields (`EXTRACTION_FAILED`).

### 6. Classification Breakdown: Acquisition vs Extraction vs Location Failures
- **Acquisition Failures (22 cells)**:
  - Scrapfly (10 cells): Akamai block pages (`BLOCKED`).
  - AlterLab (10 cells): 5 `ASYNC_INCOMPLETE` (202 Accepted), 4 `BLOCKED` (429 Rate Limit), 1 `PROVIDER_ERROR` (422).
  - String (1 cell): Read timed out (`TIMEOUT`).
  - Context.dev (1 cell): Read timed out (`TIMEOUT`).
- **Extraction Failures (2 cells)**:
  - String (2 cells): Unrendered HTML page shell returned without product JSON-LD or DOM details (Tests #09 & #10).
- **Location Validation Failures (16 cells)**:
  - **16/16 schema-validated product results** across String (7) and Context.dev (9) failed location validation (`ZIP_MISMATCH`).


---

## Forensic Conclusion

> **Based on the existing 40 tests, what have we actually proven about Kroger ZIP-aware acquisition?**

We have proven that **no third-party scraping provider in the experiment natively supports or delivers Kroger ZIP-aware acquisition**. While commercial scraping APIs (Context.dev and String) can fetch Kroger product pages by passing target URLs, their outbound requests execute without injected Kroger location headers or session cookies. Consequently, **100% of acquired product results return prices and availability bound to the provider's exit-node default ZIP code rather than the customer's requested target ZIP code**.
