#!/usr/bin/env python3
"""
Enhanced Persistence Tracker für Freqtrade
Erweiterte Logik zur Verfolgung experimenteller Verbesserungen
"""

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import rapidjson
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class ExperimentType(Enum):
    """Typen von Experimenten"""
    STRATEGY_OPTIMIZATION = "strategy_optimization"
    HYPEROPT = "hyperopt"
    PARAMETER_TUNING = "parameter_tuning"
    BACKTESTING = "backtesting"
    FREQAI = "freqai"
    LIVE_TRADING = "live_trading"
    CUSTOM = "custom"


class ExperimentStatus(Enum):
    """Status eines Experiments"""
    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class ExperimentMetrics:
    """Metriken eines Experiments"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit: float = 0.0
    profit_ratio: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    win_rate: float = 0.0
    avg_profit_per_trade: float = 0.0
    avg_winning_trade: float = 0.0
    avg_losing_trade: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    custom_metrics: Dict[str, Any] = None

    def __post_init__(self):
        if self.custom_metrics is None:
            self.custom_metrics = {}


@dataclass
class ExperimentConfiguration:
    """Konfiguration eines Experiments"""
    strategy_name: str
    timeframe: str
    pairs: List[str]
    stake_amount: float
    max_open_trades: int
    stoploss: float
    minimal_roi: Dict[str, float]
    parameters: Dict[str, Any]
    exchange_config: Dict[str, Any]
    configuration_hash: str = ""

    def __post_init__(self):
        if not self.configuration_hash:
            self.configuration_hash = self._generate_hash()

    def _generate_hash(self) -> str:
        """Generiert einen Hash für die Konfiguration"""
        config_str = json.dumps(asdict(self), sort_keys=True, default=str)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]


@dataclass
class ExperimentRecord:
    """Kompletter Experiment-Datensatz"""
    experiment_id: str
    name: str
    description: str
    experiment_type: ExperimentType
    status: ExperimentStatus
    configuration: ExperimentConfiguration
    metrics: ExperimentMetrics
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    parent_experiment_id: Optional[str] = None
    tags: List[str] = None
    notes: str = ""
    artifacts: Dict[str, str] = None  # Pfade zu Dateien
    error_message: Optional[str] = None
    version: str = "1.0"

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.artifacts is None:
            self.artifacts = {}
        if not self.updated_at:
            self.updated_at = self.created_at


class EnhancedPersistenceTracker:
    """Erweiterte Persistenz-Tracking-Klasse"""

    def __init__(self, db_path: Optional[Path] = None, config: Optional[Dict] = None):
        self.db_path = db_path or Path("experiments.db")
        self.config = config or {}
        self._lock = threading.Lock()
        self._init_database()
        self._session_cache = {}

        # Logging-Konfiguration
        self.setup_experiment_logging()

    def setup_experiment_logging(self):
        """Konfiguriert Logging für Experimente"""
        log_dir = Path("logs/experiments")
        log_dir.mkdir(parents=True, exist_ok=True)

        # Experimentspezifischer Logger
        experiment_logger = logging.getLogger("freqtrade.experiments")
        if not experiment_logger.handlers:
            handler = logging.FileHandler(log_dir / "experiments.log")
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            experiment_logger.addHandler(handler)
            experiment_logger.setLevel(logging.INFO)

    def _init_database(self):
        """Initialisiert die Experiment-Datenbank"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS experiments (
                    experiment_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    experiment_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    configuration TEXT NOT NULL,
                    metrics TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    updated_at TEXT NOT NULL,
                    parent_experiment_id TEXT,
                    tags TEXT,
                    notes TEXT,
                    artifacts TEXT,
                    error_message TEXT,
                    version TEXT DEFAULT '1.0',
                    FOREIGN KEY(parent_experiment_id) REFERENCES experiments(experiment_id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS experiment_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    experiment_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    log_level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY(experiment_id) REFERENCES experiments(experiment_id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS experiment_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    experiment_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    progress_type TEXT NOT NULL,
                    progress_value REAL NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY(experiment_id) REFERENCES experiments(experiment_id)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_experiments_type_status
                ON experiments(experiment_type, status)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_experiment_logs_id_timestamp
                ON experiment_logs(experiment_id, timestamp)
            """)

    @contextmanager
    def get_db_connection(self):
        """Context Manager für Datenbankverbindungen"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create_experiment(
        self,
        name: str,
        description: str,
        experiment_type: ExperimentType,
        configuration: ExperimentConfiguration,
        parent_experiment_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """Erstellt ein neues Experiment"""

        experiment_id = self._generate_experiment_id(name, configuration)
        current_time = datetime.now(timezone.utc)

        experiment = ExperimentRecord(
            experiment_id=experiment_id,
            name=name,
            description=description,
            experiment_type=experiment_type,
            status=ExperimentStatus.INITIALIZED,
            configuration=configuration,
            metrics=ExperimentMetrics(),
            created_at=current_time,
            updated_at=current_time,
            parent_experiment_id=parent_experiment_id,
            tags=tags or []
        )

        self._save_experiment(experiment)

        # Logging
        logger.info(f"Neues Experiment erstellt: {experiment_id} - {name}")
        self.log_experiment_event(
            experiment_id,
            "info",
            f"Experiment erstellt: {name}",
            {"type": experiment_type.value}
        )

        return experiment_id

    def _generate_experiment_id(self, name: str, config: ExperimentConfiguration) -> str:
        """Generiert eine eindeutige Experiment-ID"""
        timestamp = datetime.now(timezone.utc).isoformat()
        content = f"{name}_{config.configuration_hash}_{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]

    def start_experiment(self, experiment_id: str) -> bool:
        """Startet ein Experiment"""
        with self._lock:
            experiment = self.get_experiment(experiment_id)
            if not experiment:
                logger.error(f"Experiment {experiment_id} nicht gefunden")
                return False

            experiment.status = ExperimentStatus.RUNNING
            experiment.started_at = datetime.now(timezone.utc)
            experiment.updated_at = experiment.started_at

            self._save_experiment(experiment)

            logger.info(f"Experiment gestartet: {experiment_id}")
            self.log_experiment_event(
                experiment_id,
                "info",
                "Experiment gestartet"
            )

            return True

    def update_experiment_metrics(
        self,
        experiment_id: str,
        metrics: Dict[str, Any]
    ) -> bool:
        """Aktualisiert die Metriken eines Experiments"""
        with self._lock:
            experiment = self.get_experiment(experiment_id)
            if not experiment:
                return False

            # Aktualisiere Metriken
            for key, value in metrics.items():
                if hasattr(experiment.metrics, key):
                    setattr(experiment.metrics, key, value)
                else:
                    experiment.metrics.custom_metrics[key] = value

            experiment.updated_at = datetime.now(timezone.utc)
            self._save_experiment(experiment)

            # Progress logging
            self.log_experiment_progress(
                experiment_id,
                "metrics_update",
                experiment.metrics.total_trades,
                {"updated_metrics": list(metrics.keys())}
            )

            return True

    def complete_experiment(
        self,
        experiment_id: str,
        final_metrics: Optional[Dict[str, Any]] = None,
        artifacts: Optional[Dict[str, str]] = None
    ) -> bool:
        """Schließt ein Experiment ab"""
        with self._lock:
            experiment = self.get_experiment(experiment_id)
            if not experiment:
                return False

            experiment.status = ExperimentStatus.COMPLETED
            experiment.completed_at = datetime.now(timezone.utc)
            experiment.updated_at = experiment.completed_at

            if final_metrics:
                for key, value in final_metrics.items():
                    if hasattr(experiment.metrics, key):
                        setattr(experiment.metrics, key, value)
                    else:
                        experiment.metrics.custom_metrics[key] = value

            if artifacts:
                experiment.artifacts.update(artifacts)

            self._save_experiment(experiment)

            logger.info(f"Experiment abgeschlossen: {experiment_id}")
            self.log_experiment_event(
                experiment_id,
                "info",
                "Experiment abgeschlossen",
                {"total_trades": experiment.metrics.total_trades,
                 "profit_ratio": experiment.metrics.profit_ratio}
            )

            return True

    def fail_experiment(self, experiment_id: str, error_message: str) -> bool:
        """Markiert ein Experiment als fehlgeschlagen"""
        with self._lock:
            experiment = self.get_experiment(experiment_id)
            if not experiment:
                return False

            experiment.status = ExperimentStatus.FAILED
            experiment.error_message = error_message
            experiment.updated_at = datetime.now(timezone.utc)

            self._save_experiment(experiment)

            logger.error(f"Experiment fehlgeschlagen: {experiment_id} - {error_message}")
            self.log_experiment_event(
                experiment_id,
                "error",
                f"Experiment fehlgeschlagen: {error_message}"
            )

            return True

    def get_experiment(self, experiment_id: str) -> Optional[ExperimentRecord]:
        """Lädt ein Experiment aus der Datenbank"""
        with self.get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM experiments WHERE experiment_id = ?",
                (experiment_id,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_experiment(row)

    def list_experiments(
        self,
        experiment_type: Optional[ExperimentType] = None,
        status: Optional[ExperimentStatus] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[ExperimentRecord]:
        """Listet Experimente mit Filteroptionen"""

        where_clauses = []
        params = []

        if experiment_type:
            where_clauses.append("experiment_type = ?")
            params.append(experiment_type.value)

        if status:
            where_clauses.append("status = ?")
            params.append(status.value)

        if tags:
            # Tags sind als JSON gespeichert
            for tag in tags:
                where_clauses.append("tags LIKE ?")
                params.append(f'%"{tag}"%')

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        with self.get_db_connection() as conn:
            cursor = conn.execute(
                f"""
                SELECT * FROM experiments
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                params + [limit]
            )

            return [self._row_to_experiment(row) for row in cursor.fetchall()]

    def compare_experiments(self, experiment_ids: List[str]) -> Dict[str, Any]:
        """Vergleicht mehrere Experimente"""
        experiments = []
        for exp_id in experiment_ids:
            exp = self.get_experiment(exp_id)
            if exp:
                experiments.append(exp)

        if not experiments:
            return {}

        comparison = {
            "experiments": [],
            "best_by_metric": {},
            "summary": {}
        }

        # Sammle alle Experimente
        for exp in experiments:
            exp_data = {
                "id": exp.experiment_id,
                "name": exp.name,
                "status": exp.status.value,
                "metrics": asdict(exp.metrics),
                "duration": self._calculate_duration(exp),
                "configuration_hash": exp.configuration.configuration_hash
            }
            comparison["experiments"].append(exp_data)

        # Finde beste Werte pro Metrik
        if experiments:
            metrics_to_compare = ['total_profit', 'profit_ratio', 'win_rate',
                                'sharpe_ratio', 'max_drawdown']

            for metric in metrics_to_compare:
                best_exp = max(
                    experiments,
                    key=lambda x: getattr(x.metrics, metric, 0) or 0,
                    default=None
                )
                if best_exp:
                    comparison["best_by_metric"][metric] = {
                        "experiment_id": best_exp.experiment_id,
                        "value": getattr(best_exp.metrics, metric, 0)
                    }

        # Zusammenfassung
        comparison["summary"] = {
            "total_experiments": len(experiments),
            "completed": len([e for e in experiments if e.status == ExperimentStatus.COMPLETED]),
            "failed": len([e for e in experiments if e.status == ExperimentStatus.FAILED]),
            "avg_profit_ratio": sum(e.metrics.profit_ratio for e in experiments) / len(experiments)
        }

        return comparison

    def log_experiment_event(
        self,
        experiment_id: str,
        log_level: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Protokolliert ein Experiment-Event"""
        with self.get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO experiment_logs
                (experiment_id, timestamp, log_level, message, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    experiment_id,
                    datetime.now(timezone.utc).isoformat(),
                    log_level,
                    message,
                    json.dumps(metadata) if metadata else None
                )
            )
            conn.commit()

    def log_experiment_progress(
        self,
        experiment_id: str,
        progress_type: str,
        progress_value: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Protokolliert Experiment-Fortschritt"""
        with self.get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO experiment_progress
                (experiment_id, timestamp, progress_type, progress_value, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    experiment_id,
                    datetime.now(timezone.utc).isoformat(),
                    progress_type,
                    progress_value,
                    json.dumps(metadata) if metadata else None
                )
            )
            conn.commit()

    def get_experiment_timeline(self, experiment_id: str) -> List[Dict[str, Any]]:
        """Holt die Timeline eines Experiments"""
        timeline = []

        with self.get_db_connection() as conn:
            # Events
            cursor = conn.execute(
                """
                SELECT timestamp, 'event' as type, log_level, message, metadata
                FROM experiment_logs
                WHERE experiment_id = ?
                """,
                (experiment_id,)
            )

            for row in cursor.fetchall():
                timeline.append({
                    "timestamp": row["timestamp"],
                    "type": "event",
                    "level": row["log_level"],
                    "message": row["message"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
                })

            # Progress
            cursor = conn.execute(
                """
                SELECT timestamp, 'progress' as type, progress_type, progress_value, metadata
                FROM experiment_progress
                WHERE experiment_id = ?
                """,
                (experiment_id,)
            )

            for row in cursor.fetchall():
                timeline.append({
                    "timestamp": row["timestamp"],
                    "type": "progress",
                    "progress_type": row["progress_type"],
                    "value": row["progress_value"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
                })

        # Sortiere nach Zeitstempel
        timeline.sort(key=lambda x: x["timestamp"])
        return timeline

    def export_experiment_report(self, experiment_id: str, output_path: Path) -> bool:
        """Exportiert einen detaillierten Experiment-Bericht"""
        experiment = self.get_experiment(experiment_id)
        if not experiment:
            return False

        timeline = self.get_experiment_timeline(experiment_id)

        report = {
            "experiment": asdict(experiment),
            "timeline": timeline,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "version": "1.0"
        }

        # Konvertiere datetime-Objekte zu Strings
        def datetime_converter(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, (ExperimentType, ExperimentStatus)):
                return obj.value
            return str(obj)

        try:
            with output_path.open('w') as f:
                json.dump(report, f, indent=2, default=datetime_converter)

            logger.info(f"Experiment-Bericht exportiert: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Fehler beim Exportieren des Berichts: {e}")
            return False

    def _save_experiment(self, experiment: ExperimentRecord):
        """Speichert ein Experiment in der Datenbank"""
        with self.get_db_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO experiments
                (experiment_id, name, description, experiment_type, status,
                 configuration, metrics, created_at, started_at, completed_at,
                 updated_at, parent_experiment_id, tags, notes, artifacts,
                 error_message, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    experiment.experiment_id,
                    experiment.name,
                    experiment.description,
                    experiment.experiment_type.value,
                    experiment.status.value,
                    json.dumps(asdict(experiment.configuration), default=str),
                    json.dumps(asdict(experiment.metrics), default=str),
                    experiment.created_at.isoformat(),
                    experiment.started_at.isoformat() if experiment.started_at else None,
                    experiment.completed_at.isoformat() if experiment.completed_at else None,
                    experiment.updated_at.isoformat(),
                    experiment.parent_experiment_id,
                    json.dumps(experiment.tags),
                    experiment.notes,
                    json.dumps(experiment.artifacts),
                    experiment.error_message,
                    experiment.version
                )
            )
            conn.commit()

    def _row_to_experiment(self, row) -> ExperimentRecord:
        """Konvertiert eine Datenbankzeile zu einem ExperimentRecord"""
        return ExperimentRecord(
            experiment_id=row["experiment_id"],
            name=row["name"],
            description=row["description"],
            experiment_type=ExperimentType(row["experiment_type"]),
            status=ExperimentStatus(row["status"]),
            configuration=ExperimentConfiguration(**json.loads(row["configuration"])),
            metrics=ExperimentMetrics(**json.loads(row["metrics"])),
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]),
            parent_experiment_id=row["parent_experiment_id"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            notes=row["notes"] or "",
            artifacts=json.loads(row["artifacts"]) if row["artifacts"] else {},
            error_message=row["error_message"],
            version=row["version"]
        )

    def _calculate_duration(self, experiment: ExperimentRecord) -> Optional[float]:
        """Berechnet die Dauer eines Experiments in Sekunden"""
        if experiment.started_at and experiment.completed_at:
            return (experiment.completed_at - experiment.started_at).total_seconds()
        elif experiment.started_at:
            return (datetime.now(timezone.utc) - experiment.started_at).total_seconds()
        return None

    def cleanup_old_experiments(self, days_old: int = 30) -> int:
        """Löscht alte Experimente"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

        with self.get_db_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM experiments WHERE created_at < ?",
                (cutoff_date.isoformat(),)
            )
            deleted_count = cursor.rowcount
            conn.commit()

            logger.info(f"Alte Experimente gelöscht: {deleted_count}")
            return deleted_count


# Hilfsfunktionen für einfache Integration

def create_freqtrade_experiment_tracker(config: Dict[str, Any]) -> EnhancedPersistenceTracker:
    """Erstellt einen Experiment-Tracker für Freqtrade"""
    user_data_dir = Path(config.get('user_data_dir', 'user_data'))
    db_path = user_data_dir / 'experiments.db'

    return EnhancedPersistenceTracker(db_path=db_path, config=config)


def track_backtest_experiment(
    tracker: EnhancedPersistenceTracker,
    strategy_name: str,
    config: Dict[str, Any],
    backtest_results: Dict[str, Any]
) -> str:
    """Verfolgt ein Backtest-Experiment"""

    # Erstelle Konfiguration
    experiment_config = ExperimentConfiguration(
        strategy_name=strategy_name,
        timeframe=config.get('timeframe', '5m'),
        pairs=config.get('pair_whitelist', []),
        stake_amount=config.get('stake_amount', 0.0),
        max_open_trades=config.get('max_open_trades', 0),
        stoploss=config.get('stoploss', 0.0),
        minimal_roi=config.get('minimal_roi', {}),
        parameters=config.get('strategy_parameters', {}),
        exchange_config=config.get('exchange', {})
    )

    # Erstelle Experiment
    experiment_id = tracker.create_experiment(
        name=f"Backtest: {strategy_name}",
        description=f"Automatisches Backtest für Strategie {strategy_name}",
        experiment_type=ExperimentType.BACKTESTING,
        configuration=experiment_config,
        tags=['backtest', 'automated']
    )

    # Starte Experiment
    tracker.start_experiment(experiment_id)

    # Extrahiere Metriken aus Backtest-Ergebnissen
    if 'results_metrics' in backtest_results:
        metrics = backtest_results['results_metrics']
        tracker.update_experiment_metrics(experiment_id, {
            'total_trades': metrics.get('total_trades', 0),
            'winning_trades': metrics.get('wins', 0),
            'losing_trades': metrics.get('losses', 0),
            'total_profit': metrics.get('profit_total', 0.0),
            'profit_ratio': metrics.get('profit_ratio', 0.0),
            'max_drawdown': metrics.get('max_drawdown', 0.0),
            'win_rate': metrics.get('win_rate', 0.0)
        })

    # Schließe Experiment ab
    tracker.complete_experiment(experiment_id)

    return experiment_id


if __name__ == "__main__":
    # Beispiel-Verwendung
    tracker = EnhancedPersistenceTracker()

    # Beispiel-Konfiguration
    config = ExperimentConfiguration(
        strategy_name="TestStrategy",
        timeframe="5m",
        pairs=["BTC/USDT", "ETH/USDT"],
        stake_amount=100.0,
        max_open_trades=3,
        stoploss=-0.1,
        minimal_roi={"0": 0.1, "40": 0.0},
        parameters={"rsi_period": 14},
        exchange_config={"name": "binance"}
    )

    # Erstelle Experiment
    exp_id = tracker.create_experiment(
        name="Test Experiment",
        description="Ein Test-Experiment",
        experiment_type=ExperimentType.STRATEGY_OPTIMIZATION,
        configuration=config
    )

    print(f"Experiment erstellt: {exp_id}")

    # Liste Experimente
    experiments = tracker.list_experiments()
    print(f"Gefundene Experimente: {len(experiments)}")