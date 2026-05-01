"""Modular valuation engine for EMRGY-style hydrokinetic projects."""

from .core import (
    Asset,
    AssetPortfolio,
    AssetResult,
    Canal,
    CostCategory,
    CostLine,
    Output,
    PortfolioScaledAsset,
    PortfolioResult,
    ResourceProfile,
    Site,
)
from .assets import (
    EMRGY_PLATFORMS,
    Cabling,
    CanalLining,
    EmrgyPlatform,
    EmrgyTurbineArray,
    FloatingPVArray,
)
from .engine import ProjectValuation, ValuationEngine
from .finance import CashFlow, FinanceAssumptions, FinanceModel, FinanceResult, FinancialMetrics
from .revenue import (
    CapacityPaymentRevenue,
    FixedPriceEnergyRevenue,
    RevenueLine,
    RevenueModel,
    WaterSavingsRevenue,
)

__all__ = [
    "Asset",
    "AssetPortfolio",
    "AssetResult",
    "Canal",
    "Cabling",
    "CanalLining",
    "CapacityPaymentRevenue",
    "CashFlow",
    "CostCategory",
    "CostLine",
    "EMRGY_PLATFORMS",
    "EmrgyPlatform",
    "EmrgyTurbineArray",
    "FinanceAssumptions",
    "FinanceModel",
    "FinanceResult",
    "FinancialMetrics",
    "FixedPriceEnergyRevenue",
    "FloatingPVArray",
    "Output",
    "PortfolioScaledAsset",
    "PortfolioResult",
    "ProjectValuation",
    "ResourceProfile",
    "RevenueLine",
    "RevenueModel",
    "Site",
    "ValuationEngine",
    "WaterSavingsRevenue",
]
