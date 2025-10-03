#!/usr/bin/env python3
"""
Freqtrade Integration für Enhanced Persistence Tracker
Automatische Integration in Freqtrade-Workflows
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from freqtrade.configuration import Configuration
from freqtrade.constants import Config
from freqtrade.persistence import Trade
from freqtrade.strategy.interface import IStrategy

from enhanced_persistence_tracker import (
    EnhancedPersistenceTracker,
    ExperimentType,
    ExperimentConfiguration,
    ExperimentMetrics,
    track_backtest_experiment
)

logger = logging.getLogger(__name__)


class FreqtradeExperimentIntegration:
    """Integration des Enhanced Persistence Trackers in Freqtrade"""

    def __init__(self, config: Config):
        self.config = config
        self.user_data_dir = Path(config.get('user_data_dir', 'user_data'))
        self.tracker = EnhancedPersistenceTracker(
            db_path=self.user_data_dir / 'experiments.db',
            config=config
        )
        self.current_experiment_id: Optional[str] = None
        self._setup_experiment_directory()

    def _setup_experiment_directory(self):
        """Erstellt Verzeichnisstrukturen für Experimente"""
        experiment_dirs = [
            'experiments',
            'experiments/backtests',
            'experiments/hyperopt',
            'experiments/strategies',
            'experiments/reports'
        ]

        for dir_name in experiment_dirs:
            (self.user_data_dir / dir_name).mkdir(parents=True, exist_ok=True)

    def start_live_trading_experiment(
        self,
        strategy: IStrategy,
        experiment_name: Optional[str] = None
    ) -> str:
        """Startet ein Live-Trading-Experiment"""

        if not experiment_name:
            experiment_name = f"Live Trading: {strategy.__class__.__name__}"

        config = self._extract_strategy_config(strategy)

        experiment_id = self.tracker.create_experiment(
            name=experiment_name,
            description=f"Live-Trading-Session mit {strategy.__class__.__name__}",
            experiment_type=ExperimentType.LIVE_TRADING,
            configuration=config,
            tags=['live_trading', strategy.__class__.__name__.lower()]
        )

        self.tracker.start_experiment(experiment_id)
        self.current_experiment_id = experiment_id

        logger.info(f"Live-Trading-Experiment gestartet: {experiment_id}")
        return experiment_id

    def start_backtest_experiment(
        self,
        strategy_name: str,
        timerange: str,
        experiment_name: Optional[str] = None
    ) -> str:
        """Startet ein Backtest-Experiment"""

        if not experiment_name:
            experiment_name = f"Backtest: {strategy_name} ({timerange})"

        config = self._create_backtest_config(strategy_name, timerange)

        experiment_id = self.tracker.create_experiment(
            name=experiment_name,
            description=f"Backtest für {strategy_name} im Zeitraum {timerange}",
            experiment_type=ExperimentType.BACKTESTING,
            configuration=config,
            tags=['backtest', strategy_name.lower()]
        )

        self.tracker.start_experiment(experiment_id)
        self.current_experiment_id = experiment_id

        logger.info(f"Backtest-Experiment gestartet: {experiment_id}")
        return experiment_id

    def start_hyperopt_experiment(
        self,
        strategy_name: str,
        hyperopt_epochs: int,
        experiment_name: Optional[str] = None
    ) -> str:
        """Startet ein Hyperopt-Experiment"""

        if not experiment_name:
            experiment_name = f"Hyperopt: {strategy_name} ({hyperopt_epochs} epochs)"

        config = self._create_hyperopt_config(strategy_name, hyperopt_epochs)

        experiment_id = self.tracker.create_experiment(
            name=experiment_name,
            description=f"Hyperopt-Optimierung für {strategy_name}",
            experiment_type=ExperimentType.HYPEROPT,
            configuration=config,
            tags=['hyperopt', strategy_name.lower()]
        )

        self.tracker.start_experiment(experiment_id)
        self.current_experiment_id = experiment_id

        logger.info(f"Hyperopt-Experiment gestartet: {experiment_id}")
        return experiment_id

    def update_experiment_from_trades(self, experiment_id: Optional[str] = None):
        """Aktualisiert Experiment-Metriken basierend auf aktuellen Trades"""

        exp_id = experiment_id or self.current_experiment_id
        if not exp_id:
            logger.warning("Kein aktives Experiment für Trade-Update")
            return

        try:
            # Hole alle Trades
            trades = Trade.get_trades([]).all()

            if not trades:
                return

            # Berechne Metriken
            metrics = self._calculate_metrics_from_trades(trades)

            # Aktualisiere Experiment
            self.tracker.update_experiment_metrics(exp_id, metrics)

            logger.debug(f"Experiment-Metriken aktualisiert: {len(trades)} Trades")

        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Experiment-Metriken: {e}")

    def log_trade_event(
        self,
        trade: Trade,
        event_type: str,
        details: Dict[str, Any],
        experiment_id: Optional[str] = None
    ):
        """Protokolliert ein Trade-Event"""

        exp_id = experiment_id or self.current_experiment_id
        if not exp_id:
            return

        message = f"Trade {event_type}: {trade.pair} - {details.get('action', 'unknown')}"

        metadata = {
            'trade_id': trade.id,
            'pair': trade.pair,
            'strategy': trade.strategy,
            'event_type': event_type,
            'details': details
        }

        self.tracker.log_experiment_event(
            exp_id,
            'info',
            message,
            metadata
        )

    def log_strategy_event(
        self,
        strategy_name: str,
        event_type: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        experiment_id: Optional[str] = None
    ):
        """Protokolliert ein Strategie-Event"""

        exp_id = experiment_id or self.current_experiment_id
        if not exp_id:
            return

        full_metadata = {
            'strategy': strategy_name,
            'event_type': event_type,
            **(metadata or {})
        }

        self.tracker.log_experiment_event(
            exp_id,
            'info',
            f"[{strategy_name}] {message}",
            full_metadata
        )

    def complete_current_experiment(self, notes: Optional[str] = None):
        """Schließt das aktuelle Experiment ab"""

        if not self.current_experiment_id:
            logger.warning("Kein aktives Experiment zum Abschließen")
            return

        try:
            # Finale Metriken sammeln
            trades = Trade.get_trades([]).all()
            final_metrics = self._calculate_metrics_from_trades(trades)

            # Experiment abschließen
            self.tracker.complete_experiment(
                self.current_experiment_id,
                final_metrics=final_metrics
            )

            # Export-Bericht erstellen
            report_path = self.user_data_dir / 'experiments' / 'reports' / f"{self.current_experiment_id}_report.json"
            self.tracker.export_experiment_report(self.current_experiment_id, report_path)

            if notes:
                experiment = self.tracker.get_experiment(self.current_experiment_id)
                if experiment:
                    experiment.notes = notes
                    self.tracker._save_experiment(experiment)

            logger.info(f"Experiment abgeschlossen: {self.current_experiment_id}")
            self.current_experiment_id = None

        except Exception as e:
            logger.error(f"Fehler beim Abschließen des Experiments: {e}")

    def get_experiment_summary(self, experiment_id: Optional[str] = None) -> Dict[str, Any]:
        """Erstellt eine Zusammenfassung eines Experiments"""

        exp_id = experiment_id or self.current_experiment_id
        if not exp_id:
            return {}

        experiment = self.tracker.get_experiment(exp_id)
        if not experiment:
            return {}

        timeline = self.tracker.get_experiment_timeline(exp_id)

        return {
            'experiment_id': exp_id,
            'name': experiment.name,
            'status': experiment.status.value,
            'type': experiment.experiment_type.value,
            'created_at': experiment.created_at.isoformat(),
            'duration': self.tracker._calculate_duration(experiment),
            'metrics': {
                'total_trades': experiment.metrics.total_trades,
                'profit_ratio': experiment.metrics.profit_ratio,
                'win_rate': experiment.metrics.win_rate,
                'max_drawdown': experiment.metrics.max_drawdown
            },
            'events_count': len(timeline),
            'configuration_hash': experiment.configuration.configuration_hash
        }

    def compare_strategy_experiments(self, strategy_name: str) -> Dict[str, Any]:
        """Vergleicht alle Experimente einer Strategie"""

        # Finde alle Experimente für diese Strategie
        all_experiments = self.tracker.list_experiments(limit=1000)
        strategy_experiments = [
            exp for exp in all_experiments
            if exp.configuration.strategy_name == strategy_name
        ]

        if not strategy_experiments:
            return {"message": f"Keine Experimente für Strategie {strategy_name} gefunden"}

        experiment_ids = [exp.experiment_id for exp in strategy_experiments]
        comparison = self.tracker.compare_experiments(experiment_ids)

        return {
            'strategy': strategy_name,
            'comparison': comparison,
            'trends': self._analyze_experiment_trends(strategy_experiments)
        }

    def _extract_strategy_config(self, strategy: IStrategy) -> ExperimentConfiguration:
        """Extrahiert Konfiguration aus einer Strategie"""

        return ExperimentConfiguration(
            strategy_name=strategy.__class__.__name__,
            timeframe=getattr(strategy, 'timeframe', '5m'),
            pairs=self.config.get('pair_whitelist', []),
            stake_amount=self.config.get('stake_amount', 0.0),
            max_open_trades=self.config.get('max_open_trades', 0),
            stoploss=getattr(strategy, 'stoploss', 0.0),
            minimal_roi=getattr(strategy, 'minimal_roi', {}),
            parameters=getattr(strategy, '_ft_params_from_file', {}),
            exchange_config=self.config.get('exchange', {})
        )

    def _create_backtest_config(self, strategy_name: str, timerange: str) -> ExperimentConfiguration:
        """Erstellt Konfiguration für Backtest"""

        return ExperimentConfiguration(
            strategy_name=strategy_name,
            timeframe=self.config.get('timeframe', '5m'),
            pairs=self.config.get('pair_whitelist', []),
            stake_amount=self.config.get('stake_amount', 0.0),
            max_open_trades=self.config.get('max_open_trades', 0),
            stoploss=self.config.get('stoploss', 0.0),
            minimal_roi=self.config.get('minimal_roi', {}),
            parameters={'timerange': timerange},
            exchange_config=self.config.get('exchange', {})
        )

    def _create_hyperopt_config(self, strategy_name: str, epochs: int) -> ExperimentConfiguration:
        """Erstellt Konfiguration für Hyperopt"""

        return ExperimentConfiguration(
            strategy_name=strategy_name,
            timeframe=self.config.get('timeframe', '5m'),
            pairs=self.config.get('pair_whitelist', []),
            stake_amount=self.config.get('stake_amount', 0.0),
            max_open_trades=self.config.get('max_open_trades', 0),
            stoploss=self.config.get('stoploss', 0.0),
            minimal_roi=self.config.get('minimal_roi', {}),
            parameters={'hyperopt_epochs': epochs},
            exchange_config=self.config.get('exchange', {})
        )

    def _calculate_metrics_from_trades(self, trades: List[Trade]) -> Dict[str, Any]:
        """Berechnet Metriken aus Trade-Liste"""

        if not trades:
            return {}

        closed_trades = [t for t in trades if not t.is_open]

        if not closed_trades:
            return {'total_trades': len(trades)}

        total_profit = sum(t.close_profit or 0 for t in closed_trades)
        winning_trades = [t for t in closed_trades if (t.close_profit or 0) > 0]
        losing_trades = [t for t in closed_trades if (t.close_profit or 0) <= 0]

        metrics = {
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'total_profit': total_profit,
            'profit_ratio': total_profit / len(closed_trades) if closed_trades else 0,
            'win_rate': len(winning_trades) / len(closed_trades) if closed_trades else 0,
            'avg_profit_per_trade': total_profit / len(closed_trades) if closed_trades else 0,
            'avg_winning_trade': sum(t.close_profit for t in winning_trades) / len(winning_trades) if winning_trades else 0,
            'avg_losing_trade': sum(t.close_profit for t in losing_trades) / len(losing_trades) if losing_trades else 0
        }

        # Max Drawdown berechnen
        if closed_trades:
            cumulative_profits = []
            running_profit = 0
            for trade in closed_trades:
                running_profit += trade.close_profit or 0
                cumulative_profits.append(running_profit)

            if cumulative_profits:
                peak = cumulative_profits[0]
                max_drawdown = 0
                for profit in cumulative_profits:
                    if profit > peak:
                        peak = profit
                    drawdown = (peak - profit) / peak if peak != 0 else 0
                    max_drawdown = max(max_drawdown, drawdown)

                metrics['max_drawdown'] = max_drawdown

        return metrics

    def _analyze_experiment_trends(self, experiments: List) -> Dict[str, Any]:
        """Analysiert Trends über mehrere Experimente"""

        if len(experiments) < 2:
            return {}

        # Sortiere nach Erstellungsdatum
        sorted_experiments = sorted(experiments, key=lambda x: x.created_at)

        # Berechne Trends
        profit_ratios = [exp.metrics.profit_ratio for exp in sorted_experiments]
        win_rates = [exp.metrics.win_rate for exp in sorted_experiments]
        total_trades = [exp.metrics.total_trades for exp in sorted_experiments]

        trends = {
            'profit_ratio_trend': self._calculate_trend(profit_ratios),
            'win_rate_trend': self._calculate_trend(win_rates),
            'total_trades_trend': self._calculate_trend(total_trades),
            'experiment_count': len(experiments),
            'time_span_days': (sorted_experiments[-1].created_at - sorted_experiments[0].created_at).days
        }

        return trends

    def _calculate_trend(self, values: List[float]) -> str:
        """Berechnet einfachen Trend (steigend/fallend/stabil)"""

        if len(values) < 2:
            return "insufficient_data"

        # Entferne None-Werte
        clean_values = [v for v in values if v is not None]

        if len(clean_values) < 2:
            return "insufficient_data"

        first_half = clean_values[:len(clean_values)//2]
        second_half = clean_values[len(clean_values)//2:]

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        difference = (avg_second - avg_first) / avg_first if avg_first != 0 else 0

        if difference > 0.05:  # 5% Verbesserung
            return "improving"
        elif difference < -0.05:  # 5% Verschlechterung
            return "declining"
        else:
            return "stable"

    def generate_experiment_dashboard(self) -> Dict[str, Any]:
        """Generiert eine Dashboard-Übersicht aller Experimente"""

        experiments = self.tracker.list_experiments(limit=1000)

        dashboard = {
            'summary': {
                'total_experiments': len(experiments),
                'active_experiments': len([e for e in experiments if e.status.value == 'running']),
                'completed_experiments': len([e for e in experiments if e.status.value == 'completed']),
                'failed_experiments': len([e for e in experiments if e.status.value == 'failed'])
            },
            'by_type': {},
            'recent_experiments': [],
            'best_performers': [],
            'strategies': {}
        }

        # Gruppiere nach Typ
        for exp_type in ExperimentType:
            type_experiments = [e for e in experiments if e.experiment_type == exp_type]
            dashboard['by_type'][exp_type.value] = len(type_experiments)

        # Neueste Experimente
        recent = sorted(experiments, key=lambda x: x.created_at, reverse=True)[:5]
        dashboard['recent_experiments'] = [
            {
                'id': exp.experiment_id,
                'name': exp.name,
                'type': exp.experiment_type.value,
                'status': exp.status.value,
                'created_at': exp.created_at.isoformat()
            }
            for exp in recent
        ]

        # Beste Performer
        completed = [e for e in experiments if e.status.value == 'completed']
        best = sorted(completed, key=lambda x: x.metrics.profit_ratio, reverse=True)[:5]
        dashboard['best_performers'] = [
            {
                'id': exp.experiment_id,
                'name': exp.name,
                'strategy': exp.configuration.strategy_name,
                'profit_ratio': exp.metrics.profit_ratio,
                'win_rate': exp.metrics.win_rate
            }
            for exp in best
        ]

        # Nach Strategien gruppieren
        strategy_groups = {}
        for exp in experiments:
            strategy = exp.configuration.strategy_name
            if strategy not in strategy_groups:
                strategy_groups[strategy] = []
            strategy_groups[strategy].append(exp)

        for strategy, strategy_exps in strategy_groups.items():
            completed_strategy = [e for e in strategy_exps if e.status.value == 'completed']
            if completed_strategy:
                avg_profit = sum(e.metrics.profit_ratio for e in completed_strategy) / len(completed_strategy)
                dashboard['strategies'][strategy] = {
                    'total_experiments': len(strategy_exps),
                    'completed': len(completed_strategy),
                    'avg_profit_ratio': avg_profit,
                    'best_profit': max(e.metrics.profit_ratio for e in completed_strategy)
                }

        return dashboard


# Hilfsfunktionen für einfache Integration

def init_freqtrade_experiments(config: Config) -> FreqtradeExperimentIntegration:
    """Initialisiert die Experiment-Integration für Freqtrade"""
    return FreqtradeExperimentIntegration(config)


def log_freqtrade_trade(
    integration: FreqtradeExperimentIntegration,
    trade: Trade,
    action: str,
    details: Optional[Dict[str, Any]] = None
):
    """Hilfsfunktion zum Protokollieren von Trade-Events"""
    integration.log_trade_event(
        trade,
        action,
        details or {},
        integration.current_experiment_id
    )


# Beispiel-Verwendung für Strategy-Callbacks

class ExperimentTrackingMixin:
    """Mixin-Klasse für Strategien zur automatischen Experiment-Verfolgung"""

    def __init__(self):
        self.experiment_integration: Optional[FreqtradeExperimentIntegration] = None

    def init_experiment_tracking(self, config: Config):
        """Initialisiert Experiment-Tracking"""
        self.experiment_integration = FreqtradeExperimentIntegration(config)

    def on_experiment_trade_enter(self, trade: Trade, **kwargs):
        """Callback für Trade-Eintritt"""
        if self.experiment_integration:
            self.experiment_integration.log_trade_event(
                trade,
                'enter',
                {
                    'action': 'buy',
                    'rate': trade.open_rate,
                    'amount': trade.amount,
                    'enter_tag': trade.enter_tag
                }
            )

    def on_experiment_trade_exit(self, trade: Trade, **kwargs):
        """Callback für Trade-Austritt"""
        if self.experiment_integration:
            self.experiment_integration.log_trade_event(
                trade,
                'exit',
                {
                    'action': 'sell',
                    'rate': trade.close_rate,
                    'profit': trade.close_profit,
                    'exit_reason': trade.exit_reason
                }
            )

            # Update Metriken nach jedem Trade
            self.experiment_integration.update_experiment_from_trades()


if __name__ == "__main__":
    # Beispiel-Test
    config = {
        'user_data_dir': 'user_data',
        'pair_whitelist': ['BTC/USDT', 'ETH/USDT'],
        'stake_amount': 100,
        'max_open_trades': 3
    }

    integration = FreqtradeExperimentIntegration(config)

    # Starte ein Experiment
    exp_id = integration.start_backtest_experiment(
        'TestStrategy',
        '20240101-20240201'
    )

    print(f"Experiment gestartet: {exp_id}")

    # Dashboard generieren
    dashboard = integration.generate_experiment_dashboard()
    print(f"Dashboard: {dashboard}")