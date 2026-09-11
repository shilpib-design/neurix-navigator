"""
Local Offline Example for Neurix Acquisition Orchestrator.

Demonstrates full orchestration flow using mocked acquisition, extraction, and validation
without connecting to the internet or making external network requests.
"""

import json
from orchestrator.models import AcquisitionRequest, AcquisitionResult, OrchestrationStatus
from orchestrator.strategies import BaseAcquisitionStrategy
from orchestrator.orchestrator import AcquisitionOrchestrator, TargetExtractorRegistry, TargetValidator


class MockedBrowserStrategy(BaseAcquisitionStrategy):
    """
    Mocked browser strategy simulating successful offline CDP acquisition.
    """
    name = "mocked_browser_cdp"

    def is_available(self) -> bool:
        return True

    def acquire(self, request: AcquisitionRequest) -> AcquisitionResult:
        sample_html = """
        <html>
            <head><title>Mocked Retailer PDP</title></head>
            <body>
                <h1 id="title">Demo Product Super Widget</h1>
                <div id="price">$19.99</div>
                <div id="availability">In Stock</div>
            </body>
        </html>
        """
        return AcquisitionResult(
            success=True,
            method=self.name,
            url=request.url,
            title="Demo Product Super Widget",
            html=sample_html,
            elapsed_ms=120
        )


def mock_extractor(html: str, request: AcquisitionRequest) -> dict:
    """
    Mocked extractor extracting data from HTML.
    """
    return {
        "product_name": "Demo Product Super Widget",
        "brand": "DemoBrand",
        "price": "$19.99",
        "currency": "USD",
        "availability": "InStock"
    }


def main():
    print("=" * 70)
    print("NEURIX ACQUISITION ORCHESTRATOR - OFFLINE EXAMPLE")
    print("=" * 70)

    # 1. Create normalized request
    request = AcquisitionRequest(
        url="https://www.example.com/p/demo-widget",
        target="demo_retailer",
        parameters={"sku": "DEMO-12345"},
        requirements={"fields": ["product_name", "price", "availability"]}
    )

    print("Request Payload:")
    print(json.dumps(request.to_dict(), indent=2))

    # 2. Setup Extractor Registry & Register Mock Extractor
    registry = TargetExtractorRegistry()
    registry.register("demo_retailer", mock_extractor)

    # 3. Instantiate Orchestrator with Mocked Strategy
    orchestrator = AcquisitionOrchestrator(
        strategies=[MockedBrowserStrategy()],
        extractor_registry=registry,
        validator=TargetValidator()
    )

    # 4. Execute Orchestrator
    result = orchestrator.execute(request)

    print("\n" + "=" * 70)
    print("ORCHESTRATION RESULT OUTPUT")
    print("=" * 70)
    print(json.dumps(result.to_dict(), indent=2))
    print("=" * 70)
    print("Offline example completed successfully without network access.")


if __name__ == "__main__":
    main()
