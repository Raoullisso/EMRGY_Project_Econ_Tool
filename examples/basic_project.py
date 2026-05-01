"""Run a small EMRGY + floating PV valuation and print NPV."""

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


def main() -> None:
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
        finance_model=FinanceModel(
            FinanceAssumptions(
                analysis_years=25,
                discount_rate=0.08,
                investment_tax_credit_fraction=0.0,
            )
        ),
    )

    valuation = engine.evaluate(site, resources, portfolio)
    metrics = valuation.finance_result.metrics

    print(f"Annual energy: {valuation.portfolio_result.annual_output('energy_mwh', 'MWh'):.1f} MWh")
    print(f"Cable capacity: {valuation.portfolio_result.annual_output('cable_capacity_kw', 'kW'):.1f} kW")
    print(f"NPV: ${valuation.finance_result.npv_usd:,.0f}")
    if metrics.irr is None:
        print("IRR: not available")
    else:
        print(f"IRR: {metrics.irr:.1%}")
    if metrics.lcoe_usd_per_mwh is None:
        print("LCOE: not available")
    else:
        print(f"LCOE: ${metrics.lcoe_usd_per_mwh:,.0f}/MWh")


if __name__ == "__main__":
    main()
