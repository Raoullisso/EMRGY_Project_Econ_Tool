"""Top-level valuation orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from .core import AssetPortfolio, PortfolioResult, ResourceProfile, Site
from .finance import FinanceModel, FinanceResult
from .revenue import RevenueLine, RevenueModel


@dataclass(frozen=True)
class ProjectValuation:
    portfolio_result: PortfolioResult
    revenue_lines: Tuple[RevenueLine, ...]
    finance_result: FinanceResult


@dataclass(frozen=True)
class ValuationEngine:
    revenue_models: Sequence[RevenueModel]
    finance_model: FinanceModel

    def evaluate(
        self,
        site: Site,
        resources: ResourceProfile,
        portfolio: AssetPortfolio,
    ) -> ProjectValuation:
        portfolio_result = portfolio.evaluate(site, resources)
        revenue_lines = tuple(
            line
            for model in self.revenue_models
            for line in model.evaluate(portfolio_result, site)
        )
        finance_result = self.finance_model.evaluate(portfolio_result, revenue_lines)
        return ProjectValuation(
            portfolio_result=portfolio_result,
            revenue_lines=revenue_lines,
            finance_result=finance_result,
        )
