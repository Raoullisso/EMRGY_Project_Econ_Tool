# Architecture Note

The valuation engine is organized around the separation of assets, commercial
value models, and finance.

## Core Flow

```text
Site + ResourceProfile + AssetPortfolio
        |
        v
Base assets produce outputs and costs
        |
        v
Shared assets scale from portfolio capacity
        |
        v
Revenue/value models
        |
        v
Finance model
        |
        v
Annual cash flows and NPV / IRR / LCOE / payback
```

`Site` describes the project context. `ResourceProfile` contains annual water
velocity, water depth, solar capacity factor, availability, and hour assumptions.
`AssetPortfolio` contains the candidate design.

## Asset Catalog

The v1 asset catalog is deliberately limited:

- `EmrgyTurbineArray`: produces hydrokinetic MWh and AC capacity.
- `FloatingPVArray`: produces solar MWh, AC capacity, and estimated surface area.
- `CanalLining`: creates lining cost and physical avoided water loss.
- `Cabling`: scales cable capacity and cost from portfolio capacity and route length.

## Boundaries

Assets should not know how they get paid. EMRGY turbines and floating PV emit
standardized `energy_mwh` and `capacity_kw` outputs. Canal lining emits physical
avoided water loss in cubic meters. Revenue models decide how those outputs are
monetized.

Revenue models should not know asset physics. A fixed-price energy revenue model
only needs annual MWh. A water savings model only needs avoided water loss.

Finance should not know specific asset types. It consumes cost lines and revenue
lines, then computes annual cash flows and metrics. The main optimization metric
is available as `FinanceResult.npv_usd`.

## Optimization Optionality

The core engine evaluates one candidate design. An optimizer can sit outside the
engine and generate many candidate portfolios by changing turbine count, PV size,
canal lining scope, and cabling length or sizing margin.

This implementation preserves optionality by keeping assets stateless, returning
comparable standardized outputs, and keeping shared infrastructure as assets
instead of hidden finance assumptions.
