# Neurix Navigator v0.1

Neurix Navigator v0.1 is an autonomous, provider-agnostic web data acquisition engine. It intelligently routes customer requests across multiple data acquisition capabilities using an economic decision framework, failure-aware fallbacks, and real-time policy promotion.

## Core Architectural Design

- **Provider Agnostic**: Routing operates on **Capabilities** (`CapabilityMetadata`), not vendor brand names.
- **Economic Optimization**: Evaluates marginal unit costs, expected validation rates, and cascade probabilities.
- **Clean Customer Billing Abstraction**: Customer pricing is strictly separated from internal vendor acquisition costs and infrastructure costs.
- **Resource-Constrained Development**: Cloud-first workflow with zero external API dependency required for unit testing.

## Stage 0 & Stage 1 Foundation

- **Stage 0 (GitHub Development Foundation)**: GitHub Actions workflow (`.github/workflows/tests.yml`), DevContainer setup (`.devcontainer/devcontainer.json`), GitHub Copilot project guardrails (`.github/copilot-instructions.md`), `.gitignore`, and `.env.example`.
- **Stage 1 (Navigator Foundation)**:
  - Models (`core/models.py`): `AcquisitionRequest`, `TargetProfile`, `CapabilityMetadata`, `BillingRecord`, `PolicyState`.
  - Capability Registry (`core/registry.py`): Dynamic provider registration, geography capability filtering, sliding-window health management, and provider lifecycle (disable/enable with preserved historical metrics). Active default providers: `String`, `Scrapfly`, `Context.dev` (`AlterLab` disabled by default).
  - Rate Card Engine (`core/rate_card.py`): Provider rate cards, domain multipliers, volume pricing tiers (`VolumeTier`), effective marginal rate calculations, and consumption tracking.
  - Billing & Metering (`core/meter.py`): Independent customer pricing, internal vendor cost, infra cost, and gross margin computation.

## Running Unit Tests

Run unit tests locally using standard Python `unittest` (serial execution, in-memory mocks, zero external network calls):

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

To run only the core foundation test suite:

```bash
python3 -m unittest tests/test_navigator_v01_core.py
```

## Stage 2A Decisioning

`core.UnifiedPipeline` is the canonical Navigator execution path. It performs
target intelligence, capability filtering, economic cascade selection, bound
adapter execution, extraction, validation, telemetry/learning, policy update,
and billing. The default active capabilities are String, Scrapfly, and
Context.dev; AlterLab and browser/proxy capabilities remain registered but are
excluded from default routing.

Capabilities are executable only when enabled and explicitly bound to an
adapter through `ProviderRegistry.bind_adapter`. An unbound capability fails
with an explicit provider error; the pipeline never fabricates successful HTML.
The legacy `orchestrator/`, `scoring/`, and `telemetry/` packages remain
compatibility surfaces. Their strategy scorer does not control Navigator
execution; `EconomicOptimizer` and `PolicyEngine` do.
