#!/usr/bin/env python3
"""
Enhanced Strategy Base für Freqtrade mit automatischer Experiment-Verfolgung
Verbesserte Strategiebasis mit Persistenz-Tracking
"""

import logging
from abc import ABC
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.strategy.interface import IStrategy

try:
    from freqtrade_experiment_integration import (
        FreqtradeExperimentIntegration,
        ExperimentTrackingMixin
    )
    EXPERIMENTS_AVAILABLE = True
except ImportError:
    EXPERIMENTS_AVAILABLE = False
    FreqtradeExperimentIntegration = None
    ExperimentTrackingMixin = None

logger = logging.getLogger(__name__)


class EnhancedStrategyBase(IStrategy):
    """
    Erweiterte Strategiebasis mit automatischer Experiment-Verfolgung
    und verbesserter Persistenz für experimentelle Verbesserungen
    """

    # Strategy interface version
    INTERFACE_VERSION = 3

    # Basis-Konfiguration
    timeframe = '5m'
    can_short = False

    # Experimentelle Einstellungen
    enable_experiment_tracking = True
    experiment_auto_start = True
    experiment_log_trades = True
    experiment_log_signals = True

    def __init__(self, config: dict):
        super().__init__(config)

        # Experiment-Integration
        self.experiment_integration = None
        self.current_experiment_id: Optional[str] = None
        self._experiment_session_data = {}

        # Performance-Tracking
        self._trade_performance_history = []
        self._signal_history = []
        self._parameter_history = []

        # Persistenz-Speicher für experimentelle Daten
        self._experimental_data = {
            'strategy_iterations': 0,
            'parameter_changes': [],
            'performance_snapshots': [],
            'signal_accuracy': {},
            'trade_outcomes': []
        }

        # Initialisiere Experiment-Tracking
        if EXPERIMENTS_AVAILABLE and self.enable_experiment_tracking:
            self._init_experiment_tracking()

    def _init_experiment_tracking(self):
        """Initialisiert das Experiment-Tracking"""
        try:
            self.experiment_integration = FreqtradeExperimentIntegration(self.config)

            if self.experiment_auto_start:
                self.current_experiment_id = self._start_strategy_experiment()

            logger.info("Experiment-Tracking initialisiert")

        except Exception as e:
            logger.warning(f"Experiment-Tracking konnte nicht initialisiert werden: {e}")

    def _start_strategy_experiment(self) -> Optional[str]:
        """Startet ein neues Strategie-Experiment"""
        if not self.experiment_integration:
            return None

        try:
            experiment_name = f"Strategy Run: {self.__class__.__name__}"

            # Bestimme Experiment-Typ basierend auf Runmode
            from freqtrade.enums import RunMode
            runmode = self.config.get('runmode', RunMode.DRY_RUN)

            if runmode in [RunMode.LIVE, RunMode.DRY_RUN]:
                experiment_id = self.experiment_integration.start_live_trading_experiment(
                    self, experiment_name
                )
            else:
                # Für Backtesting wird das Experiment extern gestartet
                return None

            self._log_experiment_event(
                "strategy_start",
                f"Strategie {self.__class__.__name__} gestartet",
                {'runmode': str(runmode)}
            )

            return experiment_id

        except Exception as e:
            logger.error(f"Fehler beim Starten des Strategie-Experiments: {e}")
            return None

    def bot_start(self, **kwargs) -> None:
        """
        Wird einmal beim Start des Bots aufgerufen
        Erweitert um Experiment-Initialisierung
        """
        super().bot_start(**kwargs)

        # Basis-Experiment-Daten setzen
        self._experimental_data['bot_start_time'] = datetime.now(timezone.utc).isoformat()
        self._experimental_data['strategy_name'] = self.__class__.__name__
        self._experimental_data['config_hash'] = self._calculate_config_hash()

        self._log_experiment_event(
            "bot_start",
            f"Bot gestartet mit Strategie {self.__class__.__name__}",
            self._experimental_data
        )

    def bot_loop_start(self, **kwargs) -> None:
        """
        Wird bei jedem Bot-Loop aufgerufen
        Erweitert um kontinuierliche Experiment-Updates
        """
        super().bot_loop_start(**kwargs)

        # Aktualisiere Experiment-Daten
        self._experimental_data['strategy_iterations'] += 1

        # Sammle Performance-Snapshot alle 100 Iterationen
        if self._experimental_data['strategy_iterations'] % 100 == 0:
            self._create_performance_snapshot()

        # Update Experiment-Metriken
        if self.experiment_integration and self.current_experiment_id:
            self.experiment_integration.update_experiment_from_trades(
                self.current_experiment_id
            )

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: Optional[str],
        side: str,
        **kwargs
    ) -> bool:
        """
        Erweiterte Trade-Bestätigung mit Experiment-Logging
        """

        # Standard-Bestätigung
        confirm = super().confirm_trade_entry(
            pair, order_type, amount, rate, time_in_force,
            current_time, entry_tag, side, **kwargs
        )

        if confirm and self.experiment_log_trades:
            self._log_trade_decision(
                'entry_confirmed',
                pair,
                {
                    'order_type': order_type,
                    'amount': amount,
                    'rate': rate,
                    'entry_tag': entry_tag,
                    'side': side
                }
            )

        return confirm

    def confirm_trade_exit(
        self,
        pair: str,
        trade: Trade,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        exit_reason: str,
        current_time: datetime,
        **kwargs
    ) -> bool:
        """
        Erweiterte Trade-Exit-Bestätigung mit Experiment-Logging
        """

        # Standard-Bestätigung
        confirm = super().confirm_trade_exit(
            pair, trade, order_type, amount, rate,
            time_in_force, exit_reason, current_time, **kwargs
        )

        if confirm and self.experiment_log_trades:
            self._log_trade_decision(
                'exit_confirmed',
                pair,
                {
                    'trade_id': trade.id,
                    'order_type': order_type,
                    'amount': amount,
                    'rate': rate,
                    'exit_reason': exit_reason,
                    'profit': trade.calc_profit_ratio(rate)
                }
            )

            # Speichere Trade-Outcome für Analyse
            self._record_trade_outcome(trade, rate)

        return confirm

    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: Optional[str],
        side: str,
        **kwargs
    ) -> float:
        """
        Erweiterte Leverage-Bestimmung mit Experiment-Tracking
        """

        leverage = super().leverage(
            pair, current_time, current_rate, proposed_leverage,
            max_leverage, entry_tag, side, **kwargs
        )

        # Protokolliere Leverage-Entscheidungen
        if leverage != proposed_leverage:
            self._log_experiment_event(
                "leverage_adjustment",
                f"Leverage für {pair} angepasst: {proposed_leverage} -> {leverage}",
                {
                    'pair': pair,
                    'proposed': proposed_leverage,
                    'actual': leverage,
                    'max_leverage': max_leverage
                }
            )

        return leverage

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Basis-Implementierung für Indikatoren
        Muss von abgeleiteten Strategien überschrieben werden
        """

        # Basis-Indikatoren für alle Strategien
        dataframe = self._add_base_indicators(dataframe)

        # Experimentelle Indikator-Verfolgung
        if self.experiment_log_signals:
            self._track_indicator_computation(dataframe, metadata)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Basis-Implementierung für Entry-Signale
        Muss von abgeleiteten Strategien überschrieben werden
        """

        # Standard: Keine Entry-Signale
        dataframe.loc[:, 'enter_long'] = 0
        dataframe.loc[:, 'enter_short'] = 0

        # Signal-Tracking
        if self.experiment_log_signals:
            self._track_entry_signals(dataframe, metadata)

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Basis-Implementierung für Exit-Signale
        Muss von abgeleiteten Strategien überschrieben werden
        """

        # Standard: Keine Exit-Signale
        dataframe.loc[:, 'exit_long'] = 0
        dataframe.loc[:, 'exit_short'] = 0

        # Signal-Tracking
        if self.experiment_log_signals:
            self._track_exit_signals(dataframe, metadata)

        return dataframe

    def _add_base_indicators(self, dataframe: DataFrame) -> DataFrame:
        """Fügt Basis-Indikatoren hinzu, die alle Strategien nutzen können"""

        # RSI
        dataframe['rsi'] = self._safe_ta_rsi(dataframe['close'], timeperiod=14)

        # EMA
        dataframe['ema_20'] = self._safe_ta_ema(dataframe['close'], timeperiod=20)
        dataframe['ema_50'] = self._safe_ta_ema(dataframe['close'], timeperiod=50)

        # Volume-gewichteter Durchschnittspreis
        dataframe['vwap'] = self._calculate_vwap(dataframe)

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = self._safe_ta_bbands(
            dataframe['close'], timeperiod=20, nbdevup=2, nbdevdn=2
        )
        dataframe['bb_upper'] = bb_upper
        dataframe['bb_middle'] = bb_middle
        dataframe['bb_lower'] = bb_lower

        return dataframe

    def _safe_ta_rsi(self, close: pd.Series, timeperiod: int = 14) -> pd.Series:
        """Sichere RSI-Berechnung"""
        try:
            import talib
            return talib.RSI(close, timeperiod=timeperiod)
        except ImportError:
            # Fallback ohne TA-Lib
            return self._manual_rsi(close, timeperiod)

    def _safe_ta_ema(self, close: pd.Series, timeperiod: int = 20) -> pd.Series:
        """Sichere EMA-Berechnung"""
        try:
            import talib
            return talib.EMA(close, timeperiod=timeperiod)
        except ImportError:
            # Fallback mit pandas
            return close.ewm(span=timeperiod).mean()

    def _safe_ta_bbands(self, close: pd.Series, timeperiod: int = 20,
                       nbdevup: int = 2, nbdevdn: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Sichere Bollinger Bands-Berechnung"""
        try:
            import talib
            return talib.BBANDS(close, timeperiod=timeperiod, nbdevup=nbdevup, nbdevdn=nbdevdn)
        except ImportError:
            # Fallback-Implementierung
            middle = close.rolling(window=timeperiod).mean()
            std = close.rolling(window=timeperiod).std()
            upper = middle + (std * nbdevup)
            lower = middle - (std * nbdevdn)
            return upper, middle, lower

    def _manual_rsi(self, close: pd.Series, timeperiod: int = 14) -> pd.Series:
        """Manuelle RSI-Berechnung als Fallback"""
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=timeperiod).mean()
        avg_loss = loss.rolling(window=timeperiod).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_vwap(self, dataframe: DataFrame) -> pd.Series:
        """Berechnet Volume Weighted Average Price"""
        typical_price = (dataframe['high'] + dataframe['low'] + dataframe['close']) / 3
        vwap = (typical_price * dataframe['volume']).cumsum() / dataframe['volume'].cumsum()
        return vwap

    def _track_indicator_computation(self, dataframe: DataFrame, metadata: dict):
        """Verfolgt Indikator-Berechnungen für Experiment-Analyse"""

        if len(dataframe) == 0:
            return

        # Prüfe auf NaN-Werte in Indikatoren
        nan_indicators = []
        for col in dataframe.columns:
            if col not in ['date', 'open', 'high', 'low', 'close', 'volume']:
                if dataframe[col].isna().any():
                    nan_indicators.append(col)

        if nan_indicators:
            self._log_experiment_event(
                "indicator_warning",
                f"NaN-Werte in Indikatoren gefunden für {metadata['pair']}",
                {
                    'pair': metadata['pair'],
                    'nan_indicators': nan_indicators,
                    'dataframe_length': len(dataframe)
                }
            )

    def _track_entry_signals(self, dataframe: DataFrame, metadata: dict):
        """Verfolgt Entry-Signale für Analyse"""

        if len(dataframe) == 0:
            return

        long_signals = dataframe['enter_long'].sum()
        short_signals = dataframe['enter_short'].sum() if 'enter_short' in dataframe else 0

        signal_data = {
            'pair': metadata['pair'],
            'long_signals': int(long_signals),
            'short_signals': int(short_signals),
            'total_candles': len(dataframe),
            'signal_frequency': (long_signals + short_signals) / len(dataframe) if len(dataframe) > 0 else 0
        }

        # Speichere in Signal-History
        self._signal_history.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': 'entry',
            'data': signal_data
        })

        # Begrenze History-Größe
        if len(self._signal_history) > 1000:
            self._signal_history = self._signal_history[-500:]

    def _track_exit_signals(self, dataframe: DataFrame, metadata: dict):
        """Verfolgt Exit-Signale für Analyse"""

        if len(dataframe) == 0:
            return

        exit_long_signals = dataframe['exit_long'].sum()
        exit_short_signals = dataframe['exit_short'].sum() if 'exit_short' in dataframe else 0

        signal_data = {
            'pair': metadata['pair'],
            'exit_long_signals': int(exit_long_signals),
            'exit_short_signals': int(exit_short_signals),
            'total_candles': len(dataframe)
        }

        # Speichere in Signal-History
        self._signal_history.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': 'exit',
            'data': signal_data
        })

    def _log_trade_decision(self, decision_type: str, pair: str, details: Dict[str, Any]):
        """Protokolliert Trade-Entscheidungen"""

        self._log_experiment_event(
            f"trade_{decision_type}",
            f"Trade-Entscheidung für {pair}: {decision_type}",
            {
                'pair': pair,
                'decision_type': decision_type,
                'details': details
            }
        )

    def _record_trade_outcome(self, trade: Trade, exit_rate: float):
        """Zeichnet Trade-Ergebnisse für Analyse auf"""

        outcome = {
            'trade_id': trade.id,
            'pair': trade.pair,
            'enter_tag': trade.enter_tag,
            'exit_reason': trade.exit_reason,
            'open_rate': trade.open_rate,
            'close_rate': exit_rate,
            'profit_ratio': trade.calc_profit_ratio(exit_rate),
            'duration': (datetime.now(timezone.utc) - trade.open_date_utc).total_seconds(),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        self._experimental_data['trade_outcomes'].append(outcome)

        # Begrenze History-Größe
        if len(self._experimental_data['trade_outcomes']) > 1000:
            self._experimental_data['trade_outcomes'] = self._experimental_data['trade_outcomes'][-500:]

    def _create_performance_snapshot(self):
        """Erstellt einen Performance-Snapshot"""

        try:
            # Hole aktuelle Trades
            trades = Trade.get_trades([]).all()
            closed_trades = [t for t in trades if not t.is_open]

            if closed_trades:
                total_profit = sum(t.close_profit or 0 for t in closed_trades)
                winning_trades = len([t for t in closed_trades if (t.close_profit or 0) > 0])

                snapshot = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'total_trades': len(closed_trades),
                    'total_profit': total_profit,
                    'win_rate': winning_trades / len(closed_trades),
                    'iterations': self._experimental_data['strategy_iterations']
                }

                self._experimental_data['performance_snapshots'].append(snapshot)

                # Begrenze Snapshot-History
                if len(self._experimental_data['performance_snapshots']) > 100:
                    self._experimental_data['performance_snapshots'] = self._experimental_data['performance_snapshots'][-50:]

        except Exception as e:
            logger.warning(f"Fehler beim Erstellen des Performance-Snapshots: {e}")

    def _log_experiment_event(self, event_type: str, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Hilfsfunktion zum Protokollieren von Experiment-Events"""

        if self.experiment_integration and self.current_experiment_id:
            try:
                self.experiment_integration.log_strategy_event(
                    self.__class__.__name__,
                    event_type,
                    message,
                    metadata,
                    self.current_experiment_id
                )
            except Exception as e:
                logger.warning(f"Fehler beim Protokollieren des Experiment-Events: {e}")

    def _calculate_config_hash(self) -> str:
        """Berechnet einen Hash der aktuellen Konfiguration"""
        import hashlib
        import json

        # Relevante Config-Teile für Hash
        config_subset = {
            'timeframe': getattr(self, 'timeframe', '5m'),
            'minimal_roi': getattr(self, 'minimal_roi', {}),
            'stoploss': getattr(self, 'stoploss', 0),
            'strategy_params': getattr(self, '_ft_params_from_file', {})
        }

        config_str = json.dumps(config_subset, sort_keys=True, default=str)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]

    def get_experimental_summary(self) -> Dict[str, Any]:
        """Gibt eine Zusammenfassung der experimentellen Daten zurück"""

        summary = {
            'strategy_name': self.__class__.__name__,
            'iterations': self._experimental_data['strategy_iterations'],
            'config_hash': self._experimental_data.get('config_hash', ''),
            'experiment_id': self.current_experiment_id,
            'trade_outcomes_count': len(self._experimental_data['trade_outcomes']),
            'signal_history_count': len(self._signal_history),
            'performance_snapshots_count': len(self._experimental_data['performance_snapshots'])
        }

        # Letzte Performance-Daten
        if self._experimental_data['performance_snapshots']:
            latest_snapshot = self._experimental_data['performance_snapshots'][-1]
            summary['latest_performance'] = latest_snapshot

        # Signal-Statistiken
        if self._signal_history:
            entry_signals = [s for s in self._signal_history if s['type'] == 'entry']
            if entry_signals:
                total_signals = sum(
                    s['data']['long_signals'] + s['data'].get('short_signals', 0)
                    for s in entry_signals
                )
                summary['total_signals_generated'] = total_signals

        return summary

    def shutdown_experiment(self, notes: Optional[str] = None):
        """Beendet das aktuelle Experiment"""

        if self.experiment_integration and self.current_experiment_id:
            try:
                # Füge experimentelle Daten als Notizen hinzu
                experimental_summary = self.get_experimental_summary()
                full_notes = f"{notes}\n\nExperimentelle Zusammenfassung:\n{experimental_summary}" if notes else f"Experimentelle Zusammenfassung:\n{experimental_summary}"

                self.experiment_integration.complete_current_experiment(full_notes)

                logger.info(f"Experiment für Strategie {self.__class__.__name__} beendet")

            except Exception as e:
                logger.error(f"Fehler beim Beenden des Experiments: {e}")


# Beispiel für eine konkrete Strategie mit Enhanced Base

class ExampleEnhancedStrategy(EnhancedStrategyBase):
    """
    Beispiel-Strategie mit Enhanced Base
    """

    # Strategie-spezifische Parameter
    minimal_roi = {
        "60": 0.01,
        "30": 0.02,
        "0": 0.04
    }

    stoploss = -0.1

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Fügt Strategie-spezifische Indikatoren hinzu"""

        # Rufe Basis-Indikatoren auf
        dataframe = super().populate_indicators(dataframe, metadata)

        # Füge spezifische Indikatoren hinzu
        dataframe['rsi_overbought'] = dataframe['rsi'] > 70
        dataframe['rsi_oversold'] = dataframe['rsi'] < 30

        # EMA-Crossover
        dataframe['ema_crossover'] = (
            (dataframe['ema_20'] > dataframe['ema_50']) &
            (dataframe['ema_20'].shift(1) <= dataframe['ema_50'].shift(1))
        )

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Definiert Entry-Bedingungen"""

        # Rufe Basis-Implementierung auf
        dataframe = super().populate_entry_trend(dataframe, metadata)

        # Long Entry: RSI oversold + EMA crossover
        dataframe.loc[
            (dataframe['rsi_oversold']) &
            (dataframe['ema_crossover']) &
            (dataframe['volume'] > 0),
            'enter_long'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Definiert Exit-Bedingungen"""

        # Rufe Basis-Implementierung auf
        dataframe = super().populate_exit_trend(dataframe, metadata)

        # Long Exit: RSI overbought
        dataframe.loc[
            (dataframe['rsi_overbought']),
            'exit_long'
        ] = 1

        return dataframe


if __name__ == "__main__":
    # Test der Enhanced Strategy
    config = {
        'user_data_dir': 'user_data',
        'timeframe': '5m',
        'stake_amount': 100
    }

    strategy = ExampleEnhancedStrategy(config)
    print(f"Enhanced Strategy initialisiert: {strategy.__class__.__name__}")
    print(f"Experiment-Tracking aktiviert: {strategy.enable_experiment_tracking}")

    # Zeige experimentelle Zusammenfassung
    summary = strategy.get_experimental_summary()
    print(f"Experimentelle Zusammenfassung: {summary}")