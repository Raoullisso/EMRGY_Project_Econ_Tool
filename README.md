# EMRGY Valuation Model

This repository contains a small Python valuation engine for EMRGY-style modular
hydrokinetic and canal-adjacent projects. Assets model physical contribution and
cost, revenue models monetize standardized outputs, and finance converts annual
costs and revenues into project metrics.

## Product And Modeling Context

EMRGY builds modular distributed hydropower systems for existing water
infrastructure such as canals and waterways. The technology is hydrokinetic:
it uses the velocity of flowing water rather than traditional dam/head-pressure
hydropower. Public product material describes twin vertical-axis turbines,
the EmrgyFlume precast concrete ballast/anchor structure, EM2.x platform
geometry, and roughly 5-25 kW turbine-scale output ranges.

This v1 model keeps the asset catalog deliberately small:

- `EmrgyTurbineArray`
- `FloatingPVArray`
- `CanalLining`
- `Cabling`

## Architecture

```text
Site + ResourceProfile + AssetPortfolio
        |
        v
EMRGY turbine, floating PV, and canal lining outputs/costs
        |
        v
Cabling scales from portfolio capacity
        |
        v
Revenue models monetize standardized outputs
        |
        v
Finance model creates cash flows and metrics
        |
        v
NPV / IRR / LCOE / payback
```

Important boundaries:

- Assets know physical outputs, scalable costs, and warnings.
- Revenue models know how to monetize standardized outputs.
- Finance knows annual cash-flow timing, taxes, incentives, and metrics.
- `Cabling` can scale from portfolio `capacity_kw`.
- Optimization can sit outside the engine and generate candidate portfolios.

## Minimal Example

```python
from emrgy_valuation import (
    AssetPortfolio,
    Cabling,
    Canal,
    CanalLining,
    EmrgyTurbineArray,
    FinanceAssumptions,
    FinanceModel,
    FixedPriceEnergyRevenue,
    FloatingPVArray,
    ResourceProfile,
    Site,
    ValuationEngine,
    WaterSavingsRevenue,
)

site = Site(
    name="Demo canal hybrid",
    canal=Canal(bottom_width_m=5.0, usable_length_m=300.0, access_road=True),
)

resources = ResourceProfile(
    annual_hours=8760,
    water_velocity_m_s=1.5,
    water_depth_m=1.2,
    solar_capacity_factor=0.22,
    availability=0.95,
)

portfolio = AssetPortfolio(
    assets=[
        EmrgyTurbineArray(name="EMRGY turbines", turbine_count=2),
        FloatingPVArray(name="Floating PV", dc_capacity_kw=75),
        CanalLining(
            name="Canal lining",
            lined_area_m2=500,
            capex_per_m2_usd=45,
            avoided_water_loss_m3_per_year=8000,
        ),
        Cabling(name="Cabling", length_m=120),
    ]
)

engine = ValuationEngine(
    revenue_models=[
        FixedPriceEnergyRevenue(name="Energy revenue", price_per_mwh=95),
        WaterSavingsRevenue(name="Water savings", price_per_m3=0.35),
    ],
    finance_model=FinanceModel(FinanceAssumptions(analysis_years=25, discount_rate=0.08)),
)

valuation = engine.evaluate(site, resources, portfolio)

print(round(valuation.portfolio_result.annual_output("energy_mwh", "MWh"), 1))
print(round(valuation.finance_result.npv_usd, 0))
```

## NPV For Optimization

The finance model already computes NPV in `valuation.finance_result.metrics.npv_usd`.
There is also a convenience accessor:

```python
objective = valuation.finance_result.npv_usd
```

An outer optimization loop can generate different `AssetPortfolio` candidates
and maximize that value.

## V1 Scope

V1 is intentionally coarse. It supports annual deterministic resource
profiles, simplified hydrokinetic output, floating PV capacity-factor output,
scalable cabling costs, fixed-price energy revenue, water savings, capacity
payments, and basic project finance metrics.
Physical feasibility checks, detailed CFD, hydraulic backwater modeling,
protection studies, tax equity, dispatch optimization, stochastic hydrology, and
construction scheduling belong outside this first implementation.
