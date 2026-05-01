import unittest

from emrgy_valuation import (
    AssetPortfolio,
    Cabling,
    Canal,
    CanalLining,
    CapacityPaymentRevenue,
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


def annual_resource(velocity=1.5, depth=1.2, solar_capacity_factor=0.22):
    return ResourceProfile(
        annual_hours=8760,
        water_velocity_m_s=velocity,
        water_depth_m=depth,
        solar_capacity_factor=solar_capacity_factor,
        availability=0.95,
    )


class ValuationTests(unittest.TestCase):
    def test_emrgy_turbines_and_floating_pv_produce_energy_and_capacity(self):
        site = Site(
            name="Hybrid canal",
            canal=Canal(bottom_width_m=5.0, usable_length_m=300.0, access_road=True),
        )
        portfolio = AssetPortfolio(
            assets=[
                EmrgyTurbineArray(name="EMRGY turbines", turbine_count=2),
                FloatingPVArray(name="Floating PV", dc_capacity_kw=75),
            ]
        )

        result = portfolio.evaluate(site, annual_resource())

        self.assertAlmostEqual(result.annual_output("energy_mwh", "MWh"), 503.481, places=3)
        self.assertAlmostEqual(result.annual_output("capacity_kw", "kW"), 104.0)
        self.assertAlmostEqual(result.total_output("pv_surface_area_m2", "m2", "project"), 525.0)
        self.assertEqual(len(result.asset_results[0].outputs), 2)
        self.assertEqual(len(result.asset_results[1].outputs), 3)

    def test_shared_assets_scale_from_portfolio_capacity(self):
        site = Site(
            name="Shared infrastructure canal",
            canal=Canal(bottom_width_m=5.0, usable_length_m=300.0, access_road=True),
        )
        portfolio = AssetPortfolio(
            assets=[
                EmrgyTurbineArray(name="EMRGY turbines", turbine_count=4),
                FloatingPVArray(name="Floating PV", dc_capacity_kw=50),
                Cabling(name="Cabling", length_m=120),
            ]
        )

        result = portfolio.evaluate(site, annual_resource())

        self.assertAlmostEqual(result.annual_output("capacity_kw", "kW"), 128.0)
        self.assertAlmostEqual(result.annual_output("cable_capacity_kw", "kW"), 128.0)
        self.assertGreater(
            sum(cost.amount_usd for cost in result.costs if cost.source_asset == "Cabling"),
            128.0 * 120,
        )

    def test_canal_lining_can_create_non_energy_value(self):
        site = Site(
            name="Water savings canal",
            canal=Canal(bottom_width_m=6.0, usable_length_m=500.0, access_road=True),
        )
        portfolio = AssetPortfolio(
            assets=[
                CanalLining(
                    name="Canal lining",
                    lined_area_m2=800,
                    capex_per_m2_usd=45,
                    avoided_water_loss_m3_per_year=12000,
                )
            ]
        )
        engine = ValuationEngine(
            revenue_models=[
                WaterSavingsRevenue(name="Water value", price_per_m3=0.35),
            ],
            finance_model=FinanceModel(FinanceAssumptions(analysis_years=10, discount_rate=0.08)),
        )

        valuation = engine.evaluate(site, annual_resource(), portfolio)

        self.assertEqual(len(valuation.revenue_lines), 1)
        self.assertEqual(sum(line.amount_usd for line in valuation.revenue_lines), 4200)
        self.assertIsNone(valuation.finance_result.metrics.lcoe_usd_per_mwh)

    def test_finance_result_surfaces_npv_for_optimization(self):
        site = Site(
            name="NPV canal",
            canal=Canal(bottom_width_m=5.0, usable_length_m=300.0, access_road=True),
        )
        portfolio = AssetPortfolio(
            assets=[
                EmrgyTurbineArray(name="EMRGY turbines", turbine_count=2),
                FloatingPVArray(name="Floating PV", dc_capacity_kw=75),
                Cabling(name="Cabling", length_m=120),
            ]
        )
        engine = ValuationEngine(
            revenue_models=[
                FixedPriceEnergyRevenue(name="Energy revenue", price_per_mwh=95),
                CapacityPaymentRevenue(name="Capacity value", price_per_kw_year=10),
            ],
            finance_model=FinanceModel(FinanceAssumptions(analysis_years=25, discount_rate=0.08)),
        )

        valuation = engine.evaluate(site, annual_resource(), portfolio)

        self.assertEqual(valuation.finance_result.npv_usd, valuation.finance_result.metrics.npv_usd)
        self.assertIsInstance(valuation.finance_result.npv_usd, float)

    def test_asset_physics_do_not_depend_on_revenue_model(self):
        site = Site(
            name="Revenue-independent asset",
            canal=Canal(bottom_width_m=5.0, usable_length_m=300.0, access_road=True),
        )
        portfolio = AssetPortfolio(
            assets=[
                EmrgyTurbineArray(name="EMRGY turbines", turbine_count=1),
                FloatingPVArray(name="Floating PV", dc_capacity_kw=25),
                Cabling(name="Cabling", length_m=40),
            ]
        )

        no_revenue = ValuationEngine(
            revenue_models=[],
            finance_model=FinanceModel(FinanceAssumptions(analysis_years=5)),
        ).evaluate(site, annual_resource(), portfolio)
        energy_revenue = ValuationEngine(
            revenue_models=[FixedPriceEnergyRevenue(name="Energy revenue", price_per_mwh=100)],
            finance_model=FinanceModel(FinanceAssumptions(analysis_years=5)),
        ).evaluate(site, annual_resource(), portfolio)

        self.assertEqual(
            no_revenue.portfolio_result.annual_output("energy_mwh", "MWh"),
            energy_revenue.portfolio_result.annual_output("energy_mwh", "MWh"),
        )
        self.assertNotEqual(
            no_revenue.finance_result.npv_usd,
            energy_revenue.finance_result.npv_usd,
        )


if __name__ == "__main__":
    unittest.main()
