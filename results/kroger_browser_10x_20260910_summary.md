# Kroger Browser 10x ZIP Validation Experiment Summary

*Executed on: 2026-09-10 14:16:55 UTC*

## Test-Level Summary Matrix

| Test | ZIP | Product | Detected ZIP | Product Status | Price | Availability | Result |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| #01 | 30301 | Colgate Baking Soda Toothpaste | 30301 | PRODUCT_CONFIRMED | $1.99 | InStock | `VALIDATED` |
| #02 | 30301 | Suave Shampoo | 30301 | PRODUCT_CONFIRMED | $2.00 | InStock | `VALIDATED` |
| #03 | 30303 | Nature's Own Bread | 30303 | PRODUCT_CONFIRMED | $4.29 | InStock | `VALIDATED` |
| #04 | 30303 | Kroger Salted Butter | 30303 | PRODUCT_CONFIRMED | $3.59 | InStock | `VALIDATED` |
| #05 | 60601 | Every Man Jack Deodorant | 60601 | PRODUCT_CONFIRMED | $6.49 | InStock | `VALIDATED` |
| #06 | 60601 | Native Deodorant | 60601 | PRODUCT_CONFIRMED | $13.99 | InStock | `VALIDATED` |
| #07 | 75201 | Allegra Allergy | 75201 | PRODUCT_CONFIRMED | $39.99 | InStock | `VALIDATED` |
| #08 | 75201 | Claritin Liqui-Gels | 75201 | PRODUCT_CONFIRMED | $19.99 | InStock | `VALIDATED` |
| #09 | 77001 | Charmin Ultra Strong | 77001 | PRODUCT_CONFIRMED | $22.99 | InStock | `VALIDATED` |
| #10 | 77001 | Charmin Ultra Soft | 77001 | PRODUCT_CONFIRMED | $22.99 | InStock | `VALIDATED` |

---

## Provider-Independent Totals

- **Total Tests**: 10
- **ZIP Confirmed**: 10
- **ZIP Mismatched**: 0
- **ZIP Unverified**: 0
- **Product Confirmed**: 10
- **Product Mismatch**: 0
- **Validated**: 10
- **Validation Rate**: 100.0%
- **Timeouts**: 0
- **Other Failures**: 0
- **Average Latency**: 5436.0 ms

### Accuracies
- **ZIP Accuracy**: `1.00` (10/10)
- **Product Accuracy**: `1.00` (10/10)
- **Validated Accuracy**: `1.00` (10/10)


---

## Direct Assessment Answers

### 1. Can Neurix browser acquisition obtain ZIP-specific Kroger data?
**YES.** Neurix browser acquisition achieved **100% ZIP accuracy and 100% validation success** across all 10 Kroger product tests. Setting the location context (`x-active-modality` cookie) in the CDP browser instance successfully bound Kroger's PDP rendering to the exact target ZIP code, returning accurate ZIP-specific prices and availability.

### 2. How many of 10 tests are fully validated?
**10 out of 10 tests** were fully validated (`VALIDATED`).

### 3. Which ZIPs failed, if any?
**NONE.** All 10 tests across ZIPs `30301`, `30303`, `60601`, `75201`, and `77001` passed 100% successfully.

### 4. What was the failure reason?
**N/A.** Zero failures occurred.
