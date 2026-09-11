"""
Offline example demonstrating the deterministic Acquisition Strategy Scorer.

Constructs mocked observations for Kroger, Amazon, and Flipkart,
evaluates and ranks available strategies, and outputs formatted tables.
"""

from typing import List
from telemetry.models import AcquisitionObservation, ObservationStatus
from scoring.scorer import StrategyScorer


def generate_mock_observations() -> List[AcquisitionObservation]:
    obs: List[AcquisitionObservation] = []

    # -------------------------------------------------------------
    # 1. Kroger Observations
    # -------------------------------------------------------------
    # Browser CDP: 10 attempts, 10 success, 10 validated, 0 cost, avg ~1200ms
    for _ in range(10):
        obs.append(
            AcquisitionObservation(
                target="kroger",
                acquisition_method="browser_cdp",
                url="https://www.kroger.com/p/0004000042431",
                acquisition_success=True,
                elapsed_ms=1200,
                bytes=450000,
                extraction_success=True,
                extracted_fields=["product_name", "price", "upc"],
                validated=True,
                acquisition_cost=0.0,
                final_status=ObservationStatus.VALIDATED
            )
        )

    # Vendor API: 10 attempts, 8 success, 5 validated, $0.02 cost per attempt, avg ~450ms
    for i in range(10):
        if i < 5:
            # Validated
            obs.append(
                AcquisitionObservation(
                    target="kroger",
                    acquisition_method="vendor_api",
                    url="https://api.vendor.com/kroger/0004000042431",
                    acquisition_success=True,
                    elapsed_ms=450,
                    bytes=12000,
                    extraction_success=True,
                    extracted_fields=["product_name", "price"],
                    validated=True,
                    acquisition_cost=0.02,
                    final_status=ObservationStatus.VALIDATED
                )
            )
        elif i < 8:
            # Validation Failed
            obs.append(
                AcquisitionObservation(
                    target="kroger",
                    acquisition_method="vendor_api",
                    url="https://api.vendor.com/kroger/0004000042431",
                    acquisition_success=True,
                    elapsed_ms=500,
                    bytes=8000,
                    extraction_success=True,
                    extracted_fields=["product_name"],
                    validated=False,
                    acquisition_cost=0.02,
                    final_status=ObservationStatus.VALIDATION_FAILED
                )
            )
        else:
            # Acquisition Failed
            obs.append(
                AcquisitionObservation(
                    target="kroger",
                    acquisition_method="vendor_api",
                    url="https://api.vendor.com/kroger/0004000042431",
                    acquisition_success=False,
                    elapsed_ms=600,
                    bytes=0,
                    extraction_success=False,
                    validated=False,
                    acquisition_cost=0.02,
                    final_status=ObservationStatus.ACQUISITION_FAILED
                )
            )

    # -------------------------------------------------------------
    # 2. Amazon Observations
    # -------------------------------------------------------------
    # Browser CDP: 10 attempts, 10 success, 10 validated, 0 cost, avg ~1500ms
    for _ in range(10):
        obs.append(
            AcquisitionObservation(
                target="amazon",
                acquisition_method="browser_cdp",
                url="https://www.amazon.in/dp/B078Y2PJL4",
                acquisition_success=True,
                elapsed_ms=1500,
                bytes=600000,
                extraction_success=True,
                extracted_fields=["product_name", "price", "asin"],
                validated=True,
                acquisition_cost=0.0,
                final_status=ObservationStatus.VALIDATED
            )
        )

    # -------------------------------------------------------------
    # 3. Flipkart Observations
    # -------------------------------------------------------------
    # Browser CDP: 10 attempts, 10 success, 10 validated, 0 cost, avg ~1800ms
    for _ in range(10):
        obs.append(
            AcquisitionObservation(
                target="flipkart",
                acquisition_method="browser_cdp",
                url="https://www.flipkart.com/p/itmffgx6p6c2wgda",
                acquisition_success=True,
                elapsed_ms=1800,
                bytes=550000,
                extraction_success=True,
                extracted_fields=["product_name", "price", "product_id"],
                validated=True,
                acquisition_cost=0.0,
                final_status=ObservationStatus.VALIDATED
            )
        )

    return obs


def main():
    observations = generate_mock_observations()
    scorer = StrategyScorer()

    targets = ["kroger", "amazon", "flipkart"]
    available_methods = ["browser_cdp", "vendor_api"]

    for target in targets:
        print(f"\nTARGET: {target}")
        print("=" * 110)
        ranked = scorer.rank_strategies(
            target=target,
            observations=observations,
            available_methods=available_methods
        )

        header = f"{'Rank':<5} | {'Method':<15} | {'Samples':<8} | {'Validation':<10} | {'Success':<8} | {'Latency':<10} | {'Cost/Validated':<15} | {'Confidence':<10} | {'Score':<6}"
        print(header)
        print("-" * 110)

        for rank, score in enumerate(ranked, start=1):
            val_pct = f"{score.validation_rate * 100:.1f}%"
            succ_pct = f"{score.success_rate * 100:.1f}%"
            lat_str = f"{score.average_latency_ms:.1f}ms"
            cost_str = f"${score.cost_per_validated_result:.4f}"
            conf_str = f"{score.confidence * 100:.0f}%"

            row = (
                f"{rank:<5} | "
                f"{score.acquisition_method:<15} | "
                f"{score.sample_size:<8} | "
                f"{val_pct:<10} | "
                f"{succ_pct:<8} | "
                f"{lat_str:<10} | "
                f"{cost_str:<15} | "
                f"{conf_str:<10} | "
                f"{score.score:.4f}"
            )
            print(row)

        recommendation = scorer.recommend(target, observations, available_methods)
        if recommendation:
            print(f"\nRecommended strategy: {recommendation.acquisition_method}")
        else:
            print("\nRecommended strategy: None")


if __name__ == "__main__":
    main()
