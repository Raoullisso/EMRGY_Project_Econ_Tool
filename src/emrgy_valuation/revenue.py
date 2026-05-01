"""Revenue and value models.

Revenue models consume standardized outputs from the portfolio result. They
do not inspect asset classes or asset implementation details.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Sequence, Tuple

from .core import PortfolioResult, Site


@dataclass(frozen=True)
class RevenueLine:
    name: str
    amount_usd: float
    year: int = 1
    recurring: bool = True
    escalation_rate: float = 0.0
    source_model: Optional[str] = None

    def amount_for_year(self, year: int) -> float:
        if self.recurring:
            if year < self.year:
                return 0.0
            elapsed = year - self.year
            return self.amount_usd * ((1 + self.escalation_rate) ** elapsed)
        if year == self.year:
            return self.amount_usd
        return 0.0


class RevenueModel(Protocol):
    name: str

    def evaluate(self, portfolio: PortfolioResult, site: Site) -> Sequence[RevenueLine]:
        ...


@dataclass(frozen=True)
class FixedPriceEnergyRevenue:
    """Monetizes annual energy output at a fixed or escalating price."""

    name: str
    price_per_mwh: float
    output_kind: str = "energy_mwh"
    escalation_rate: float = 0.0

    def evaluate(self, portfolio: PortfolioResult, site: Site) -> Tuple[RevenueLine, ...]:
        del site
        mwh = portfolio.annual_output(self.output_kind, unit="MWh")
        if mwh == 0:
            return ()
        return (
            RevenueLine(
                name=self.name,
                amount_usd=mwh * self.price_per_mwh,
                year=1,
                recurring=True,
                escalation_rate=self.escalation_rate,
                source_model=self.name,
            ),
        )


@dataclass(frozen=True)
class WaterSavingsRevenue:
    """Monetizes avoided water loss."""

    name: str
    price_per_m3: float
    output_kind: str = "avoided_water_loss_m3"
    escalation_rate: float = 0.0

    def evaluate(self, portfolio: PortfolioResult, site: Site) -> Tuple[RevenueLine, ...]:
        del site
        saved_m3 = portfolio.annual_output(self.output_kind, unit="m3")
        if saved_m3 == 0:
            return ()
        return (
            RevenueLine(
                name=self.name,
                amount_usd=saved_m3 * self.price_per_m3,
                year=1,
                recurring=True,
                escalation_rate=self.escalation_rate,
                source_model=self.name,
            ),
        )


@dataclass(frozen=True)
class CapacityPaymentRevenue:
    """Simple annual capacity payment for eligible kW."""

    name: str
    price_per_kw_year: float
    output_kind: str = "capacity_kw"
    escalation_rate: float = 0.0

    def evaluate(self, portfolio: PortfolioResult, site: Site) -> Tuple[RevenueLine, ...]:
        del site
        capacity_kw = portfolio.annual_output(self.output_kind, unit="kW")
        if capacity_kw == 0:
            return ()
        return (
            RevenueLine(
                name=self.name,
                amount_usd=capacity_kw * self.price_per_kw_year,
                year=1,
                recurring=True,
                escalation_rate=self.escalation_rate,
                source_model=self.name,
            ),
        )
