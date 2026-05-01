"""V1 asset evaluators.

The active asset catalog is intentionally small:

- EMRGY turbines
- Floating PV panels
- Canal lining
- Cabling

Assets know their own physical contribution, costs, and warnings. Shared assets
can scale from portfolio outputs. Assets intentionally do not know how outputs
are monetized.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional

from .core import (
    AssetResult,
    CostCategory,
    CostLine,
    Output,
    PortfolioResult,
    ResourceProfile,
    Site,
)


@dataclass(frozen=True)
class EmrgyPlatform:
    """Public EMRGY platform geometry used for coarse site screening."""

    name: str
    length_m: float
    height_m: float
    width_m: float
    weight_kg: float
    rotor_height_min_m: float
    rotor_height_max_m: float
    blade_diameter_m: float


EMRGY_PLATFORMS = {
    "EM2.0": EmrgyPlatform("EM2.0", 2.4, 2.3, 4.8, 14000, 0.6, 1.8, 1.36),
    "EM2.1": EmrgyPlatform("EM2.1", 2.4, 2.3, 3.6, 12000, 0.6, 1.8, 1.00),
    "EM2.2": EmrgyPlatform("EM2.2", 2.4, 4.2, 4.8, 18500, 0.6, 4.0, 1.36),
}


@dataclass(frozen=True)
class EmrgyTurbineArray:
    """EMRGY hydrokinetic turbine array with simplified energy physics."""

    name: str
    turbine_count: int
    platform: str = "EM2.1"
    rated_kw_per_turbine: float = 22.0
    rated_velocity_m_s: float = 1.5
    cut_in_velocity_m_s: float = 1.0
    survival_velocity_m_s: float = 4.0
    water_to_wire_efficiency: float = 0.70
    installed_cost_per_turbine_usd: float = 175000.0
    fixed_annual_opex_usd: float = 5000.0
    variable_opex_per_turbine_usd: float = 2500.0
    performance_derate: float = 1.0
    metadata: Mapping[str, object] = field(default_factory=dict)

    def evaluate(self, site: Site, resources: ResourceProfile) -> AssetResult:
        if self.turbine_count < 0:
            raise ValueError("turbine_count cannot be negative.")
        if self.platform not in EMRGY_PLATFORMS:
            raise ValueError(f"Unknown EMRGY platform: {self.platform}")

        platform = EMRGY_PLATFORMS[self.platform]
        warnings = []

        if site.canal.bottom_width_m < platform.width_m:
            warnings.append(
                (
                    f"{self.name} uses {platform.name}, which typically needs about "
                    f"{platform.width_m:.1f} m canal width; site has "
                    f"{site.canal.bottom_width_m:.1f} m."
                )
            )

        velocity = resources.water_velocity_m_s
        depth = resources.water_depth_m
        if velocity is None:
            warnings.append("Missing water velocity; EMRGY output set to zero.")
            power_kw = 0.0
        elif velocity < self.cut_in_velocity_m_s:
            warnings.append(f"Water velocity {velocity:.2f} m/s is below cut-in speed.")
            power_kw = 0.0
        elif velocity > self.survival_velocity_m_s:
            warnings.append(
                f"Water velocity {velocity:.2f} m/s exceeds survival speed "
                f"{self.survival_velocity_m_s:.2f} m/s; output set to zero."
            )
            power_kw = 0.0
        else:
            velocity_fraction = min((velocity / self.rated_velocity_m_s) ** 3, 1.0)
            power_kw = (
                self.turbine_count
                * self.rated_kw_per_turbine
                * velocity_fraction
                * resources.availability
                * self.performance_derate
            )

        if depth is None:
            warnings.append("Missing water depth; depth not screened.")
        elif depth < 0.5 or depth > 3.85:
            warnings.append(
                f"Water depth {depth:.2f} m is outside the coarse public site "
                "guidance range of 0.5-3.85 m."
            )

        annual_energy_mwh = power_kw * resources.annual_hours / 1000

        nameplate_kw = self.turbine_count * self.rated_kw_per_turbine
        capex = self.turbine_count * self.installed_cost_per_turbine_usd
        annual_opex = self.fixed_annual_opex_usd + (
            self.variable_opex_per_turbine_usd * self.turbine_count
        )

        return AssetResult(
            asset_name=self.name,
            outputs=(
                Output(
                    kind="energy_mwh",
                    quantity=annual_energy_mwh,
                    unit="MWh",
                    period="annual",
                    source_asset=self.name,
                    metadata={
                        "resource": "hydrokinetic",
                        "platform": platform.name,
                        "water_to_wire_efficiency": self.water_to_wire_efficiency,
                    },
                ),
                Output(
                    kind="capacity_kw",
                    quantity=nameplate_kw,
                    unit="kW",
                    period="annual",
                    source_asset=self.name,
                    metadata={"resource": "hydrokinetic"},
                ),
            ),
            costs=(
                CostLine(
                    name=f"{self.name} installed cost",
                    category=CostCategory.CAPEX,
                    amount_usd=capex,
                    source_asset=self.name,
                ),
                CostLine(
                    name=f"{self.name} annual O&M",
                    category=CostCategory.OPEX,
                    amount_usd=annual_opex,
                    year=1,
                    recurring=True,
                    source_asset=self.name,
                ),
            ),
            warnings=tuple(warnings),
        )


@dataclass(frozen=True)
class FloatingPVArray:
    """Floating PV array with simple capacity-factor energy production."""

    name: str
    dc_capacity_kw: float
    dc_ac_ratio: float = 1.25
    installed_cost_per_kw_dc_usd: float = 1300.0
    annual_opex_per_kw_dc_usd: float = 22.0
    water_surface_area_m2_per_kw_dc: float = 7.0
    performance_derate: float = 1.0
    metadata: Mapping[str, object] = field(default_factory=dict)

    def evaluate(self, site: Site, resources: ResourceProfile) -> AssetResult:
        if self.dc_capacity_kw < 0:
            raise ValueError("dc_capacity_kw cannot be negative.")
        if self.dc_ac_ratio <= 0:
            raise ValueError("dc_ac_ratio must be positive.")

        warnings = []
        capacity_factor = resources.solar_capacity_factor
        if capacity_factor is None:
            warnings.append("Missing solar capacity factor; PV output set to zero.")
            annual_energy_mwh = 0.0
        else:
            annual_energy_mwh = (
                self.dc_capacity_kw
                * capacity_factor
                * resources.annual_hours
                * resources.availability
                * self.performance_derate
                / 1000
            )

        water_area = self.dc_capacity_kw * self.water_surface_area_m2_per_kw_dc
        if site.canal.water_surface_area_m2 is not None and water_area > site.canal.water_surface_area_m2:
            warnings.append(
                f"{self.name}: estimated PV area {water_area:.0f} m2 exceeds "
                f"site water surface area {site.canal.water_surface_area_m2:.0f} m2."
            )

        ac_capacity_kw = self.dc_capacity_kw / self.dc_ac_ratio
        return AssetResult(
            asset_name=self.name,
            outputs=(
                Output(
                    kind="energy_mwh",
                    quantity=annual_energy_mwh,
                    unit="MWh",
                    period="annual",
                    source_asset=self.name,
                    metadata={"resource": "solar"},
                ),
                Output(
                    kind="capacity_kw",
                    quantity=ac_capacity_kw,
                    unit="kW",
                    period="annual",
                    source_asset=self.name,
                    metadata={"resource": "solar", "basis": "ac"},
                ),
                Output(
                    kind="pv_surface_area_m2",
                    quantity=water_area,
                    unit="m2",
                    period="project",
                    source_asset=self.name,
                ),
            ),
            costs=(
                CostLine(
                    name=f"{self.name} installed cost",
                    category=CostCategory.CAPEX,
                    amount_usd=self.dc_capacity_kw * self.installed_cost_per_kw_dc_usd,
                    source_asset=self.name,
                ),
                CostLine(
                    name=f"{self.name} annual O&M",
                    category=CostCategory.OPEX,
                    amount_usd=self.dc_capacity_kw * self.annual_opex_per_kw_dc_usd,
                    year=1,
                    recurring=True,
                    source_asset=self.name,
                ),
            ),
            warnings=tuple(warnings),
        )


@dataclass(frozen=True)
class CanalLining:
    """Canal lining asset that creates physical avoided water loss."""

    name: str
    lined_area_m2: float
    capex_per_m2_usd: float
    annual_opex_usd: float = 0.0
    avoided_water_loss_m3_per_year: float = 0.0

    def evaluate(self, site: Site, resources: ResourceProfile) -> AssetResult:
        del resources
        warnings = []
        if site.canal.water_surface_area_m2 is None:
            warnings.append(f"{self.name}: site usable length is missing; lining area not screened.")

        costs = [
            CostLine(
                name=f"{self.name} lining installation",
                category=CostCategory.CAPEX,
                amount_usd=self.lined_area_m2 * self.capex_per_m2_usd,
                source_asset=self.name,
            )
        ]
        if self.annual_opex_usd:
            costs.append(
                CostLine(
                    name=f"{self.name} lining maintenance",
                    category=CostCategory.OPEX,
                    amount_usd=self.annual_opex_usd,
                    year=1,
                    recurring=True,
                    source_asset=self.name,
                )
            )

        outputs = []
        if self.avoided_water_loss_m3_per_year:
            outputs.append(
                Output(
                    kind="avoided_water_loss_m3",
                    quantity=self.avoided_water_loss_m3_per_year,
                    unit="m3",
                    period="annual",
                    source_asset=self.name,
                )
            )
        return AssetResult(
            asset_name=self.name,
            outputs=tuple(outputs),
            costs=tuple(costs),
            warnings=tuple(warnings),
        )


@dataclass(frozen=True)
class Cabling:
    """Electrical cabling allowance that scales with total portfolio capacity."""

    name: str
    length_m: float
    fixed_installed_cost_usd: float = 5000.0
    installed_cost_per_kw_m_usd: float = 12.0
    annual_opex_fraction_of_capex: float = 0.005
    sizing_margin: float = 1.0

    def evaluate_with_portfolio(
        self,
        site: Site,
        resources: ResourceProfile,
        portfolio: PortfolioResult,
    ) -> AssetResult:
        del site, resources
        capacity_kw = portfolio.annual_output("capacity_kw", unit="kW") * self.sizing_margin
        capex = self.fixed_installed_cost_usd + (
            capacity_kw * self.length_m * self.installed_cost_per_kw_m_usd
        )
        return AssetResult(
            asset_name=self.name,
            outputs=(
                Output(
                    kind="cable_capacity_kw",
                    quantity=capacity_kw,
                    unit="kW",
                    period="annual",
                    source_asset=self.name,
                    metadata={"length_m": self.length_m},
                ),
            ),
            costs=(
                CostLine(
                    name=f"{self.name} installed cost",
                    category=CostCategory.CAPEX,
                    amount_usd=capex,
                    source_asset=self.name,
                ),
                CostLine(
                    name=f"{self.name} annual inspection",
                    category=CostCategory.OPEX,
                    amount_usd=capex * self.annual_opex_fraction_of_capex,
                    year=1,
                    recurring=True,
                    source_asset=self.name,
                ),
            ),
        )
