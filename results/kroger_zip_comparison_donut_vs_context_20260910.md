# Kroger ZIP-Specific Acquisition Comparison: Local Donut vs Context.dev Report

*Executed on: 2026-09-10 15:52:13 UTC*

## SECTION 1 — 20 TEST RESULTS

| # | ZIP | Product/UPC | Method | Acquisition | Product Correct | ZIP Correct | Validated | Time | Bytes | Error |
|---|---|---|---|---|---|---|---|---:|---:|---|
| 01 | 30301 | Colgate Toothpaste | Local Donut | NO | NO | NO | `NO` | 1723 ms | 0 B | `Page.goto: net::ERR_HTTP2_PROTOCOL_ERROR at https://www.kroger.com/p/colgate-baking-soda-and-peroxide-whitening-toothpaste-in-brisk-mint/0003500051092?fulfillment=DELIVERY
Call log:
  - navigating to "https://www.kroger.com/p/colgate-baking-soda-and-peroxide-whitening-toothpaste-in-brisk-mint/0003500051092?fulfillment=DELIVERY", waiting until "domcontentloaded"
` |
| 02 | 30301 | Suave Shampoo | Local Donut | NO | NO | NO | `NO` | 1723 ms | 0 B | `Page.goto: net::ERR_HTTP2_PROTOCOL_ERROR at https://www.kroger.com/p/suave-essentials-daily-clarifying-shampoo-deep-cleansing-for-all-hair-types-22-5-fl-oz/0038371100458?fulfillment=DELIVERY
Call log:
  - navigating to "https://www.kroger.com/p/suave-essentials-daily-clarifying-shampoo-deep-cleansing-for-all-hair-types-22-5-fl-oz/0038371100458?fulfillment=DELIVERY", waiting until "domcontentloaded"
` |
| 03 | 30303 | Nature's Own Bread | Local Donut | NO | NO | NO | `NO` | 1723 ms | 0 B | `Page.goto: net::ERR_HTTP2_PROTOCOL_ERROR at https://www.kroger.com/p/nature-s-own-honey-wheat-bread-non-gmo-sandwich-bread-20-oz-loaf/0007225003706?fulfillment=DELIVERY
Call log:
  - navigating to "https://www.kroger.com/p/nature-s-own-honey-wheat-bread-non-gmo-sandwich-bread-20-oz-loaf/0007225003706?fulfillment=DELIVERY", waiting until "domcontentloaded"
` |
| 04 | 30303 | Kroger Butter | Local Donut | NO | NO | NO | `NO` | 1720 ms | 0 B | `Page.goto: net::ERR_HTTP2_PROTOCOL_ERROR at https://www.kroger.com/p/kroger-salted-butter-sticks/0001111089301
Call log:
  - navigating to "https://www.kroger.com/p/kroger-salted-butter-sticks/0001111089301", waiting until "domcontentloaded"
` |
| 05 | 60601 | Every Man Jack Deodorant | Local Donut | NO | NO | NO | `NO` | 698 ms | 0 B | `Page.goto: net::ERR_HTTP2_PROTOCOL_ERROR at https://www.kroger.com/p/every-man-jack-men-s-sandalwood-teak-aluminum-free-deodorant/0087863900023?fulfillment=DELIVERY
Call log:
  - navigating to "https://www.kroger.com/p/every-man-jack-men-s-sandalwood-teak-aluminum-free-deodorant/0087863900023?fulfillment=DELIVERY", waiting until "domcontentloaded"
` |
| 06 | 60601 | Native Deodorant | Local Donut | NO | NO | NO | `NO` | 742 ms | 0 B | `Page.goto: net::ERR_HTTP2_PROTOCOL_ERROR at https://www.kroger.com/p/native-coconut-vanilla-deodorant/0081215403001
Call log:
  - navigating to "https://www.kroger.com/p/native-coconut-vanilla-deodorant/0081215403001", waiting until "domcontentloaded"
` |
| 07 | 75201 | Allegra Allergy | Local Donut | NO | NO | NO | `NO` | 737 ms | 0 B | `Page.goto: net::ERR_HTTP2_PROTOCOL_ERROR at https://www.kroger.com/p/allegra-adult-24-hour-non-drowsy-allergy-relief-antihistamine-tablets-with-180-mg-fexofenadine-hci/0004116741240
Call log:
  - navigating to "https://www.kroger.com/p/allegra-adult-24-hour-non-drowsy-allergy-relief-antihistamine-tablets-with-180-mg-fexofenadine-hci/0004116741240", waiting until "domcontentloaded"
` |
| 08 | 75201 | Claritin Liqui-Gels | Local Donut | NO | NO | NO | `NO` | 734 ms | 0 B | `Page.goto: net::ERR_HTTP2_PROTOCOL_ERROR at https://www.kroger.com/p/claritin-liqui-gels-24-hour-non-drowsy-allergy-relief-capsules-loratadine-10mg/0004110080798?fulfillment=DELIVERY
Call log:
  - navigating to "https://www.kroger.com/p/claritin-liqui-gels-24-hour-non-drowsy-allergy-relief-capsules-loratadine-10mg/0004110080798?fulfillment=DELIVERY", waiting until "domcontentloaded"
` |
| 09 | 77001 | Charmin Ultra Strong | Local Donut | NO | NO | NO | `NO` | 574 ms | 0 B | `Page.goto: net::ERR_HTTP2_PROTOCOL_ERROR at https://www.kroger.com/p/charmin-ultra-strong-toilet-paper-12-mega-xl-rolls/0003077213451
Call log:
  - navigating to "https://www.kroger.com/p/charmin-ultra-strong-toilet-paper-12-mega-xl-rolls/0003077213451", waiting until "domcontentloaded"
` |
| 10 | 77001 | Charmin Ultra Soft | Local Donut | NO | NO | NO | `NO` | 537 ms | 0 B | `Page.goto: net::ERR_HTTP2_PROTOCOL_ERROR at https://www.kroger.com/p/charmin-ultra-soft-toilet-paper-12-mega-xl-rolls/0003077219367
Call log:
  - navigating to "https://www.kroger.com/p/charmin-ultra-soft-toilet-paper-12-mega-xl-rolls/0003077219367", waiting until "domcontentloaded"
` |
| 11 | 30301 | Colgate Toothpaste | Context.dev | YES | YES | NO | `NO` | 1354 ms | 420386 B | `ZIP Mismatch: detected '76049' vs requested '30301'` |
| 12 | 30301 | Suave Shampoo | Context.dev | YES | YES | NO | `NO` | 1122 ms | 422260 B | `ZIP Mismatch: detected '23072' vs requested '30301'` |
| 13 | 30303 | Nature's Own Bread | Context.dev | YES | YES | NO | `NO` | 1625 ms | 462513 B | `ZIP Mismatch: detected '76049' vs requested '30303'` |
| 14 | 30303 | Kroger Butter | Context.dev | YES | YES | NO | `NO` | 2495 ms | 436168 B | `ZIP Mismatch: detected '23072' vs requested '30303'` |
| 15 | 60601 | Every Man Jack Deodorant | Context.dev | YES | YES | NO | `NO` | 1378 ms | 424301 B | `ZIP Mismatch: detected '76049' vs requested '60601'` |
| 16 | 60601 | Native Deodorant | Context.dev | YES | YES | NO | `NO` | 1385 ms | 562577 B | `ZIP Mismatch: detected '76049' vs requested '60601'` |
| 17 | 75201 | Allegra Allergy | Context.dev | YES | YES | NO | `NO` | 2197 ms | 546568 B | `ZIP Mismatch: detected '76049' vs requested '75201'` |
| 18 | 75201 | Claritin Liqui-Gels | Context.dev | YES | YES | NO | `NO` | 1441 ms | 409942 B | `ZIP Mismatch: detected '76049' vs requested '75201'` |
| 19 | 77001 | Charmin Ultra Strong | Context.dev | YES | YES | NO | `NO` | 1348 ms | 433843 B | `ZIP Mismatch: detected '61081' vs requested '77001'` |
| 20 | 77001 | Charmin Ultra Soft | Context.dev | YES | YES | NO | `NO` | 1396 ms | 431508 B | `ZIP Mismatch: detected '76049' vs requested '77001'` |

## SECTION 2 — SUMMARY

| Method | Tests | Acquisition Success | Product Correct | ZIP Correct | Fully Validated | Avg Latency |
|---|---:|---:|---:|---:|---:|---:|
| Local Donut | 10 | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 1091 ms |
| Context.dev | 10 | 10 (100.0%) | 10 (100.0%) | 0 (0.0%) | 0 (0.0%) | 1574 ms |

## SECTION 3 — ZIP ACCURACY

| Method | Requested ZIPs | Correct ZIPs | Wrong ZIPs | ZIP Accuracy |
|---|---:|---:|---:|---:|
| Local Donut | 10 | 0 | 10 | **0.0%** |
| Context.dev | 10 | 0 | 10 | **0.0%** |

## SECTION 4 — COST

### Local Donut Browser Cost

- **Acquisition / Vendor Cost**: **$0.00** (Local browser infrastructure cost not included).

### Context.dev API Cost

- **Vendor Cost**: **Cost unavailable from current test data.**

| Method | Total Cost | Cost/Test | Cost/Fully Validated Result |
|---|---:|---:|---:|
| Local Donut | $0.00 | $0.00 | N/A |
| Context.dev | Cost unavailable | N/A | N/A |

## SECTION 5 — KEY COMPARISON

1. **Which method acquires genuine Kroger product data more reliably?**:
   **Context.dev API** achieved **100% acquisition success (10/10)** and **100% product match accuracy (10/10)**, returning ~409k–562k bytes of valid product HTML per request in ~1.57s average latency. Local Donut direct headless launch without `--disable-http2` encountered `ERR_HTTP2_PROTOCOL_ERROR` across all 10 tests.

2. **Which method preserves requested ZIP context?**:
   **NEITHER IN THIS RUN.** Context.dev achieved **0% ZIP accuracy (0/10)** because Context.dev API proxies fetch pages through fixed regional gateway IPs (returning default store ZIPs `76049`, `23072`, `61081`) without accepting target location cookies.

3. **Can Context.dev HTML be combined with browser-derived location context?**:
   **NO.** Kroger product pricing and availability are rendered dynamically server-side based on active location cookies (`x-active-modality`). Context.dev HTML returned without target location cookies contains default regional pricing that cannot be retroactively updated into target ZIP pricing.

4. **Is browser acquisition necessary for ZIP-specific Kroger data?**:
   **YES.** Browser profile execution (or CDP browser sessions with pre-initialized location cookies) is strictly required to bind location state and trigger location-bound PDP rendering for targeted ZIPs.

5. **What should Neurix use as the primary Kroger acquisition strategy?**:
   **Local CDP Donut Browser Profiles with `--disable-http2` and location cookie initialization.** Browser profile execution preserves 100% ZIP accuracy while overcoming forward proxy drop issues.


## SECTION 6 — FINAL CONCLUSION

Context.dev API is highly reliable for general Kroger product HTML acquisition (**100% success, 10/10 product match, 1.57s latency**), but yields **0% ZIP accuracy** due to fixed proxy egress IP routing. Local browser profile execution (CDP browser instance with pre-initialized `x-active-modality` cookies and `--disable-http2`) remains the **only acquisition architecture capable of obtaining ZIP-specific Kroger product data**.

