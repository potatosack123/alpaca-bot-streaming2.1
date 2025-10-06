# bot/strategy/gap_and_go.py - FIXED VERSION
from __future__ import annotations
from typing import Optional, Dict
from datetime import time, datetime
from collections import deque
import pytz

from ..state import SessionState, Signal, SignalType, Bar
from .base import StrategyBase

class GapAndGo(StrategyBase):
    name = "GapAndGo"
    default_timeframe = "1m"
    supported_timeframes = {"1m"}

    def __init__(self,
                 min_gap_pct: float = 3.0,          # Lowered from 10% to 3% (more realistic)
                 max_price: float = 50.0,           # Raised to $50 (too restrictive at $15)
                 max_float_m: float = 500.0,        # Raised to 500M (we don't have float data anyway)
                 confirm_bars: int = 0,             # 0 = immediate break
                 trade_cutoff_minute: int = 5,      # First 5 minutes after open
                 exit_time_hour: int = 15,          # Exit at 3pm if still holding
                 exit_time_minute: int = 0
    ):
        self.min_gap_pct = min_gap_pct
        self.max_price = max_price
        self.max_float_m = max_float_m
        self.confirm_bars = confirm_bars
        self.trade_cutoff_minute = trade_cutoff_minute
        self.exit_time_hour = exit_time_hour
        self.exit_time_minute = exit_time_minute
        
        # State tracking
        self.premarket_high: Dict[str, float] = {}
        self.previous_close: Dict[str, float] = {}   # NEW: track previous close as fallback
        self.first_break_done: Dict[str, bool] = {}
        self.buffer: Dict[str, deque] = {}
        self.in_position: Dict[str, bool] = {}       # NEW: track if we're in a position
        self.current_date: Dict[str, str] = {}       # NEW: track current trading date
        
        self.east = pytz.timezone("America/New_York")

    def on_start(self, session_state: SessionState) -> None:
        self.premarket_high.clear()
        self.previous_close.clear()
        self.first_break_done.clear()
        self.buffer.clear()
        self.in_position.clear()
        self.current_date.clear()

    def _get_eastern_time(self, bar: Bar) -> datetime:
        """Convert bar timestamp to Eastern time"""
        if not bar.timestamp:
            return None
        if bar.timestamp.tzinfo is None:
            utc_time = bar.timestamp.replace(tzinfo=pytz.UTC)
        else:
            utc_time = bar.timestamp
        return utc_time.astimezone(self.east)

    def _is_premarket(self, eastern_time: datetime) -> bool:
        """Check if time is premarket (4am-9:30am ET)"""
        t = eastern_time.time()
        return time(4, 0) <= t < time(9, 30)

    def _is_market_hours(self, eastern_time: datetime) -> bool:
        """Check if time is during market hours (9:30am-4pm ET)"""
        t = eastern_time.time()
        return time(9, 30) <= t <= time(16, 0)

    def _should_exit(self, eastern_time: datetime) -> bool:
        """Check if we should exit the position (after exit time)"""
        t = eastern_time.time()
        exit_t = time(self.exit_time_hour, self.exit_time_minute)
        return t >= exit_t

    def _reset_daily_state(self, symbol: str, date_str: str):
        """Reset state for a new trading day"""
        if self.current_date.get(symbol) != date_str:
            self.current_date[symbol] = date_str
            self.first_break_done[symbol] = False
            self.buffer[symbol] = deque(maxlen=max(1, self.confirm_bars))
            self.in_position[symbol] = False
            # Don't clear premarket_high - let it accumulate during premarket

    def on_bar(self, symbol: str, bar: Bar, state: SessionState) -> Optional[Signal]:
        """
        Gap-and-go strategy:
        1. Track premarket high (or use previous close if no premarket data)
        2. Enter when price breaks above premarket high in first N minutes
        3. Exit at 3pm or on gap fill
        """
        eastern_time = self._get_eastern_time(bar)
        if not eastern_time:
            return None
        
        date_str = eastern_time.strftime("%Y-%m-%d")
        self._reset_daily_state(symbol, date_str)
        
        # === PREMARKET: Track the high ===
        if self._is_premarket(eastern_time):
            ph = self.premarket_high.get(symbol, float("-inf"))
            self.premarket_high[symbol] = max(ph, bar.high)
            return None
        
        # === AFTER HOURS: Track close for next day ===
        if not self._is_market_hours(eastern_time):
            # Update previous close for tomorrow's gap calculation
            self.previous_close[symbol] = bar.close
            return None
        
        # === MARKET HOURS ===
        
        # Get reference high (premarket high or previous close)
        ref_high = self.premarket_high.get(symbol)
        if ref_high is None or ref_high == float("-inf"):
            # No premarket data - use previous close as fallback
            ref_high = self.previous_close.get(symbol)
            if ref_high is None:
                # First day of backtest - use first bar's open as reference
                ref_high = bar.open
                self.premarket_high[symbol] = ref_high
        
        # Check if we're in a position and should exit
        if self.in_position.get(symbol, False):
            # Exit at specified time (default 3pm)
            if self._should_exit(eastern_time):
                self.in_position[symbol] = False
                return Signal(SignalType.SELL)
            
            # Optional: Exit if price goes back below reference (gap fill)
            # if bar.close < ref_high * 0.98:  # 2% below entry level
            #     self.in_position[symbol] = False
            #     return Signal(SignalType.SELL)
            
            return None  # Hold position
        
        # Only trade in first N minutes after open
        t = eastern_time.time()
        minutes_since_open = (eastern_time.hour - 9) * 60 + (eastern_time.minute - 30)
        if minutes_since_open > self.trade_cutoff_minute:
            return None
        
        # Skip if already entered today
        if self.first_break_done.get(symbol, False):
            return None
        
        # Check for breakout with optional confirmation bars
        buf = self.buffer.setdefault(symbol, deque(maxlen=max(1, self.confirm_bars)))
        buf.append(bar.close)
        
        # Breakout condition: high breaks above reference AND close above reference
        broke = bar.high >= ref_high and bar.close >= ref_high
        
        if self.confirm_bars > 0:
            # Require N consecutive closes above reference
            broke = broke and len(buf) == self.confirm_bars and all(x >= ref_high for x in buf)
        
        if broke:
            self.first_break_done[symbol] = True
            self.in_position[symbol] = True
            return Signal(SignalType.BUY)
        
        return None

    def on_stop(self, session_state: SessionState) -> None:
        """Cleanup when strategy stops"""
        pass
