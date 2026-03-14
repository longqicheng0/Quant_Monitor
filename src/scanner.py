"""Backward-compatible scanner exports.

This module remains for compatibility with earlier imports.
Prefer using src.core.scanner for new code.
"""

from src.core.models import ScanStatus, SignalEvent
from src.core.scanner import StrategyScanner

# Keep old class name available to avoid breaking existing imports.
AberrationScanner = StrategyScanner

__all__ = ["SignalEvent", "ScanStatus", "StrategyScanner", "AberrationScanner"]
