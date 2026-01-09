"""
Stub for HyperoptTools - hyperopt functionality has been removed.

This stub exists to prevent import errors in strategy code that was designed 
for hyperoptimization.
"""

import logging
from pathlib import Path
from typing import Any, Dict

from freqtrade.constants import Config
from freqtrade.enums import HyperoptState

logger = logging.getLogger(__name__)


class HyperoptStateContainer:
    """
    Stub for hyperopt state container.
    
    Hyperopt functionality has been removed, so state is always NOT_RUNNING.
    """
    state: HyperoptState = HyperoptState.DATALOAD


class HyperoptTools:
    """
    Stub class for hyperopt tools.
    
    Hyperopt functionality has been removed from this execution engine.
    This stub prevents import errors but does nothing.
    """

    @staticmethod
    def load_params(filename: Path) -> Dict[str, Any]:
        """
        Stub for loading hyperopt parameters from file.
        
        Returns empty dict since hyperopt is removed.
        """
        logger.warning(
            f"Hyperopt has been removed. Ignoring parameter file: {filename}"
        )
        return {}

    @staticmethod
    def has_space(config: Config, space: str) -> bool:
        """
        Stub for checking if hyperopt space is active.
        
        Always returns False since hyperopt is removed.
        """
        return False
