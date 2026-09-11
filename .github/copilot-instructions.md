# GitHub Copilot Instructions for Neurix Navigator v0.1

## Core Architecture & Design Principles

1. **Provider Agnostic**: Navigator is strictly provider-agnostic. Never hardcode vendor-specific routing logic, vendor names, or domain-specific vendor chains into the decision engine or core orchestrator.
2. **Capability Abstraction**: Providers are replaceable execution targets. Routing logic operates exclusively on **Capabilities** (`CapabilityMetadata`), not vendor brand names.
3. **Dynamic Provider Integration**: New providers must be addable via configuration, the `ProviderRegistry`, and adapter mechanisms without requiring changes or refactoring of the decision engine or pipeline.
4. **Geography & Country Capabilities**: Target country requirement is an internal target intelligence attribute inferred via `TargetProfile`. Customer requests are not required to specify location explicitly. Routing filters capabilities by geographical support metadata.

## Security & Resource Safety Rules

1. **No Hardcoded Credentials**: Never commit API keys, passwords, tokens, proxy credentials, or secrets to the repository.
2. **Deterministic Unit Testing**: Never perform live vendor or external API network calls inside unit tests. Use mocked/in-memory providers and fixtures.
3. **No Unintentional Browser Spawns**: Never launch browser instances (Chromium, Playwright, CDP, Donut) or proxy sessions unless explicitly authorized for targeted integration runs.
4. **Preserve Working Adapters**: Do not modify working browser/CDP/acquisition code unless strictly required for compatibility.
5. **Lightweight & Targeted Testing**: Keep code changes small and modular. Always run targeted unit tests serially before broader tests.
6. **No Credit Consumption**: Do not consume vendor API credits during automated testing or development.
