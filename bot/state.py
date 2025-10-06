from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

# -------- Strategy slot (multi-strategy UI) --------
@dataclass
class StrategySlot:
    enabled: bool = False
    name: str = "BaselineSMA"
    priority: int = 1
    start_hhmm: str = "09:30"
    end_hhmm: str = "16:00"

    # NEW: per-slot timeframe (UI choice) and lunch skip
    timeframe: str = "1m"                  # "1m" | "3m" | "5m"  (current strategies run on 1m; others can aggregate later)
    lunch_skip: Optional[bool] = None      # None → use global; True/False → override for this slot

    use_global: bool = True
    risk_percent: Optional[float] = None
    sl_percent: Optional[float] = None
    tp_percent: Optional[float] = None
# -------- Core enums --------
class RunMode(Enum):
    LIVE = "live"
    BACKTEST = "backtest"

class ForceMode(Enum):
    AUTO = "auto"
    PAPER = "paper"
    LIVE = "live"

class SignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    FLAT = "flat"

class BacktestSource(Enum):
    ALPACA = "alpaca"
    YAHOO = "yahoo"
    CSV = "csv"

# -------- Bars & signals --------
@dataclass
class Bar:
    timestamp: Optional[datetime]
    open: float
    high: float
    low: float
    close: float
    volume: int

@dataclass
class Signal:
    type: SignalType
    sl_pct: Optional[float] = None
    tp_pct: Optional[float] = None
    meta: Dict[str, Any] = field(default_factory=dict)

# -------- Settings & session state --------
@dataclass
class AppSettings:
    symbols: str = "AAPL,MSFT"
    timeframe: str = "1m"  # '1m' | '3m' | '5m'
    lunch_skip: bool = True
    risk_percent: float = 1.0
    stop_loss_percent: float = 1.0
    take_profit_percent: float = 2.0
    selected_strategy: str = "BaselineSMA"
    flatten_on_stop: bool = False
    force_mode: ForceMode = ForceMode.AUTO
    extra_strategy_paths: List[str] = field(default_factory=list)
    backtest_years: int = 3
    backtest_source: BacktestSource = BacktestSource.ALPACA
    data_feed: str = "IEX"  # historical feed preference for adapter compatibility
    # NEW: multi-strategy slots (empty by default; nothing changes until you use them)
    strategy_slots: List[StrategySlot] = field(default_factory=list)

@dataclass
class SessionState:
    run_mode: RunMode = RunMode.BACKTEST
    connection_mode: Optional[str] = None  # 'paper' | 'live'
    started: bool = False
    paused: bool = False
    should_stop: bool = False
    flatten_on_stop: bool = False

    # P/L
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    last_pl_update: Optional[datetime] = None

    # Backtest
    run_folder: Optional[Path] = None
    stats: Dict[str, Any] = field(default_factory=dict)
