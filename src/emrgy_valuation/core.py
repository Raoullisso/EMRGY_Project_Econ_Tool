"""Core domain contracts for modular project valuation.

The core deliberately avoids EMRGY-specific asset physics, tariffs, and
finance rules. Assets emit standardized results, revenue models monetize
outputs, and finance consumes annualized cash-flow lines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Optional, Protocol, Sequence, Tuple, runtime_checkable


class CostCategory(str, Enum):
    """High-level cost categories consumed by the finance layer."""

    CAPEX = "capex"
    OPEX = "opex"
    REPLACEMENT = "replacement"
    DECOMMISSIONING = "decommissioning"
    DEVELOPMENT = "development"
    FIXED = "fixed"


@dataclass(frozen=True)
class Canal:
    """Physical canal context used by canal and hydrokinetic assets."""

    bottom_width_m: float
    usable_length_m: Optional[float] = None
    slope_m_per_m: Optional[float] = None
    lining: Optional[str] = None
    access_road: bool = True
    debris_level: str = "minimal"

    @property
    def water_surface_area_m2(self) -> Optional[float]:
        if self.usable_length_m is None:
            return None
        return self.bottom_width_m * self.usable_length_m


@dataclass(frozen=True)
class Site:
    """Physical and commercial context for a project candidate."""

    name: str
    canal: Canal
    utility_territory: Optional[str] = None
    tax_jurisdiction: Optional[str] = None
    project_life_years: int = 25
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ResourceProfile:
    """Annual project resource assumptions.

    The model intentionally stays at annual resolution for now. Assets use
    these assumptions to produce annual generation and sizing outputs.
    """

    annual_hours: float = 8760.0
    water_velocity_m_s: Optional[float] = None
    water_depth_m: Optional[float] = None
    availability: float = 1.0
    solar_capacity_factor: Optional[float] = None

    @property
    def total_hours(self) -> float:
        return self.annual_hours


@dataclass(frozen=True)
class Output:
    """Standardized physical or economic output from an asset."""

    kind: str
    quantity: float
    unit: str
    period: Optional[str] = None
    source_asset: Optional[str] = None
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CostLine:
    """A cost contribution that finance can place into annual cash flows."""

    name: str
    category: CostCategory
    amount_usd: float
    year: int = 0
    recurring: bool = False
    escalation_rate: float = 0.0
    source_asset: Optional[str] = None

    def amount_for_year(self, year: int) -> float:
        if self.recurring:
            if year < self.year:
                return 0.0
            elapsed = year - self.year
            return self.amount_usd * ((1 + self.escalation_rate) ** elapsed)
        if year == self.year:
            return self.amount_usd
        return 0.0


@dataclass(frozen=True)
class AssetResult:
    """Standard output shape for all asset evaluators."""

    asset_name: str
    outputs: Tuple[Output, ...] = ()
    costs: Tuple[CostLine, ...] = ()
    warnings: Tuple[str, ...] = ()


class Asset(Protocol):
    """Stateless evaluator for one project component."""

    name: str

    def evaluate(self, site: Site, resources: ResourceProfile) -> AssetResult:
        ...


@runtime_checkable
class PortfolioScaledAsset(Protocol):
    """Asset whose cost or size scales from the rest of the portfolio."""

    name: str

    def evaluate_with_portfolio(
        self,
        site: Site,
        resources: ResourceProfile,
        portfolio: "PortfolioResult",
    ) -> AssetResult:
        ...


@dataclass(frozen=True)
class PortfolioResult:
    """Aggregated physical result for a candidate project design."""

    asset_results: Tuple[AssetResult, ...]

    @property
    def outputs(self) -> Tuple[Output, ...]:
        return tuple(output for result in self.asset_results for output in result.outputs)

    @property
    def costs(self) -> Tuple[CostLine, ...]:
        return tuple(cost for result in self.asset_results for cost in result.costs)

    @property
    def warnings(self) -> Tuple[str, ...]:
        return tuple(warning for result in self.asset_results for warning in result.warnings)

    def total_output(self, kind: str, unit: Optional[str] = None, period: Optional[str] = None) -> float:
        total = 0.0
        for output in self.outputs:
            if output.kind != kind:
                continue
            if unit is not None and output.unit != unit:
                continue
            if period is not None and output.period != period:
                continue
            total += output.quantity
        return total

    def annual_output(self, kind: str, unit: Optional[str] = None) -> float:
        total = 0.0
        for output in self.outputs:
            if output.kind != kind:
                continue
            if unit is not None and output.unit != unit:
                continue
            if output.period != "annual":
                continue
            total += output.quantity
        return total


@dataclass(frozen=True)
class AssetPortfolio:
    """A candidate set of project assets to evaluate together.

    Standard assets are evaluated first. Portfolio-scaled assets such as
    cabling are evaluated second using the preliminary portfolio outputs.
    """

    assets: Sequence[object]

    def evaluate(self, site: Site, resources: ResourceProfile) -> PortfolioResult:
        base_results = []
        scaled_assets = []
        for asset in self.assets:
            if isinstance(asset, PortfolioScaledAsset):
                scaled_assets.append(asset)
            else:
                base_results.append(asset.evaluate(site, resources))

        preliminary = PortfolioResult(asset_results=tuple(base_results))
        scaled_results = tuple(
            asset.evaluate_with_portfolio(site, resources, preliminary) for asset in scaled_assets
        )
        return PortfolioResult(asset_results=tuple(base_results) + scaled_results)
