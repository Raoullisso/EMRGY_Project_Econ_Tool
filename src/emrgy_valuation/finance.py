"""Asset-agnostic project finance calculations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Sequence, Tuple

from .core import CostCategory, CostLine, PortfolioResult
from .revenue import RevenueLine


@dataclass(frozen=True)
class FinanceAssumptions:
    analysis_years: int = 25
    discount_rate: float = 0.08
    tax_rate: float = 0.0
    investment_tax_credit_fraction: float = 0.0
    depreciation_years: Optional[int] = None


@dataclass(frozen=True)
class CashFlow:
    year: int
    revenue_usd: float
    capex_usd: float
    opex_usd: float
    replacement_usd: float
    decommissioning_usd: float
    development_usd: float
    incentives_usd: float
    tax_usd: float

    @property
    def total_cost_usd(self) -> float:
        return (
            self.capex_usd
            + self.opex_usd
            + self.replacement_usd
            + self.decommissioning_usd
            + self.development_usd
        )

    @property
    def net_cash_flow_usd(self) -> float:
        return self.revenue_usd + self.incentives_usd - self.total_cost_usd - self.tax_usd


@dataclass(frozen=True)
class FinancialMetrics:
    npv_usd: float
    irr: Optional[float]
    lcoe_usd_per_mwh: Optional[float]
    simple_payback_year: Optional[int]
    total_revenue_usd: float
    total_cost_usd: float
    total_energy_mwh: float


@dataclass(frozen=True)
class FinanceResult:
    cash_flows: Tuple[CashFlow, ...]
    metrics: FinancialMetrics

    @property
    def npv_usd(self) -> float:
        """Convenience accessor for optimization loops."""

        return self.metrics.npv_usd


@dataclass(frozen=True)
class FinanceModel:
    assumptions: FinanceAssumptions

    def evaluate(
        self,
        portfolio: PortfolioResult,
        revenue_lines: Sequence[RevenueLine],
    ) -> FinanceResult:
        years = range(0, self.assumptions.analysis_years + 1)
        capex_basis = _cost_total_for_categories(
            portfolio.costs,
            categories=(CostCategory.CAPEX, CostCategory.DEVELOPMENT),
            years=years,
        )
        annual_depreciation = _annual_depreciation(
            capex_basis=capex_basis,
            depreciation_years=self.assumptions.depreciation_years,
        )

        cash_flows = []
        for year in years:
            revenue = sum(line.amount_for_year(year) for line in revenue_lines)
            categorized_costs = _costs_for_year(portfolio.costs, year)
            incentives = 0.0
            if year == 1 and self.assumptions.investment_tax_credit_fraction:
                incentives = capex_basis * self.assumptions.investment_tax_credit_fraction

            taxable_income = (
                revenue
                - categorized_costs[CostCategory.OPEX]
                - categorized_costs[CostCategory.REPLACEMENT]
                - annual_depreciation.get(year, 0.0)
            )
            tax = max(taxable_income, 0.0) * self.assumptions.tax_rate

            cash_flows.append(
                CashFlow(
                    year=year,
                    revenue_usd=revenue,
                    capex_usd=categorized_costs[CostCategory.CAPEX],
                    opex_usd=categorized_costs[CostCategory.OPEX],
                    replacement_usd=categorized_costs[CostCategory.REPLACEMENT],
                    decommissioning_usd=categorized_costs[CostCategory.DECOMMISSIONING],
                    development_usd=categorized_costs[CostCategory.DEVELOPMENT]
                    + categorized_costs[CostCategory.FIXED],
                    incentives_usd=incentives,
                    tax_usd=tax,
                )
            )

        metrics = _metrics(
            cash_flows=cash_flows,
            portfolio=portfolio,
            discount_rate=self.assumptions.discount_rate,
        )
        return FinanceResult(cash_flows=tuple(cash_flows), metrics=metrics)


def _costs_for_year(costs: Iterable[CostLine], year: int) -> Dict[CostCategory, float]:
    totals = {category: 0.0 for category in CostCategory}
    for cost in costs:
        totals[cost.category] += cost.amount_for_year(year)
    return totals


def _cost_total_for_categories(
    costs: Iterable[CostLine],
    categories: Sequence[CostCategory],
    years: Iterable[int],
) -> float:
    total = 0.0
    category_set = set(categories)
    year_tuple = tuple(years)
    for cost in costs:
        if cost.category not in category_set:
            continue
        total += sum(cost.amount_for_year(year) for year in year_tuple)
    return total


def _annual_depreciation(
    capex_basis: float,
    depreciation_years: Optional[int],
) -> Dict[int, float]:
    if depreciation_years is None or depreciation_years <= 0:
        return {}
    annual = capex_basis / depreciation_years
    return {year: annual for year in range(1, depreciation_years + 1)}


def _metrics(
    cash_flows: Sequence[CashFlow],
    portfolio: PortfolioResult,
    discount_rate: float,
) -> FinancialMetrics:
    net_cash_flows = [cash_flow.net_cash_flow_usd for cash_flow in cash_flows]
    npv = _npv(net_cash_flows, discount_rate)
    irr = _irr(net_cash_flows)
    payback = _simple_payback_year(net_cash_flows)

    total_energy_mwh = portfolio.annual_output("energy_mwh", unit="MWh") * (
        len(cash_flows) - 1
    )
    discounted_energy = sum(
        portfolio.annual_output("energy_mwh", unit="MWh") / ((1 + discount_rate) ** year)
        for year in range(1, len(cash_flows))
    )
    discounted_costs = sum(
        (
            cash_flow.total_cost_usd
            - cash_flow.incentives_usd
            + cash_flow.tax_usd
        )
        / ((1 + discount_rate) ** cash_flow.year)
        for cash_flow in cash_flows
    )
    lcoe = None
    if discounted_energy > 0:
        lcoe = discounted_costs / discounted_energy

    return FinancialMetrics(
        npv_usd=npv,
        irr=irr,
        lcoe_usd_per_mwh=lcoe,
        simple_payback_year=payback,
        total_revenue_usd=sum(cash_flow.revenue_usd for cash_flow in cash_flows),
        total_cost_usd=sum(cash_flow.total_cost_usd for cash_flow in cash_flows),
        total_energy_mwh=total_energy_mwh,
    )


def _npv(cash_flows: Sequence[float], discount_rate: float) -> float:
    return sum(value / ((1 + discount_rate) ** year) for year, value in enumerate(cash_flows))


def _irr(cash_flows: Sequence[float]) -> Optional[float]:
    has_positive = any(value > 0 for value in cash_flows)
    has_negative = any(value < 0 for value in cash_flows)
    if not has_positive or not has_negative:
        return None

    low = -0.9999
    high = 10.0
    low_npv = _npv(cash_flows, low)
    if low_npv * _npv(cash_flows, high) > 0:
        return None

    for _ in range(200):
        mid = (low + high) / 2
        mid_npv = _npv(cash_flows, mid)
        if abs(mid_npv) < 1e-7:
            return mid
        if low_npv * mid_npv <= 0:
            high = mid
        else:
            low = mid
            low_npv = mid_npv
    return (low + high) / 2


def _simple_payback_year(cash_flows: Sequence[float]) -> Optional[int]:
    cumulative = 0.0
    for year, value in enumerate(cash_flows):
        cumulative += value
        if cumulative >= 0 and year > 0:
            return year
    return None
