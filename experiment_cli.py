#!/usr/bin/env python3
"""
CLI-Tool für Enhanced Persistence Tracker
Kommandozeilen-Interface zur Verwaltung von Freqtrade-Experimenten
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from tabulate import tabulate

try:
    from enhanced_persistence_tracker import (
        EnhancedPersistenceTracker,
        ExperimentType,
        ExperimentStatus,
        ExperimentConfiguration
    )
    from freqtrade_experiment_integration import FreqtradeExperimentIntegration
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Fehler beim Importieren der Module: {e}")
    MODULES_AVAILABLE = False


class ExperimentCLI:
    """Command Line Interface für Experiment-Management"""

    def __init__(self, db_path: Optional[Path] = None):
        if not MODULES_AVAILABLE:
            print("Erforderliche Module nicht verfügbar. Installieren Sie die Abhängigkeiten.")
            sys.exit(1)

        self.db_path = db_path or Path("experiments.db")
        self.tracker = EnhancedPersistenceTracker(self.db_path)

    def list_experiments(
        self,
        experiment_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        output_format: str = "table"
    ):
        """Listet Experimente auf"""

        # Konvertiere String-Parameter
        exp_type = ExperimentType(experiment_type) if experiment_type else None
        exp_status = ExperimentStatus(status) if status else None

        experiments = self.tracker.list_experiments(
            experiment_type=exp_type,
            status=exp_status,
            limit=limit
        )

        if not experiments:
            print("Keine Experimente gefunden.")
            return

        # Bereite Daten für Ausgabe vor
        data = []
        for exp in experiments:
            data.append({
                'ID': exp.experiment_id[:8],
                'Name': exp.name[:30],
                'Typ': exp.experiment_type.value,
                'Status': exp.status.value,
                'Strategie': exp.configuration.strategy_name,
                'Trades': exp.metrics.total_trades,
                'Profit%': f"{exp.metrics.profit_ratio:.2%}" if exp.metrics.profit_ratio else "0.00%",
                'Win Rate': f"{exp.metrics.win_rate:.2%}" if exp.metrics.win_rate else "0.00%",
                'Erstellt': exp.created_at.strftime('%Y-%m-%d %H:%M')
            })

        self._output_data(data, output_format, "Experimente")

    def show_experiment(self, experiment_id: str, include_timeline: bool = False):
        """Zeigt Details eines Experiments"""

        experiment = self.tracker.get_experiment(experiment_id)
        if not experiment:
            print(f"Experiment {experiment_id} nicht gefunden.")
            return

        # Basis-Informationen
        print(f"\n=== Experiment Details: {experiment.experiment_id} ===")
        print(f"Name: {experiment.name}")
        print(f"Beschreibung: {experiment.description}")
        print(f"Typ: {experiment.experiment_type.value}")
        print(f"Status: {experiment.status.value}")
        print(f"Erstellt: {experiment.created_at}")
        print(f"Gestartet: {experiment.started_at}")
        print(f"Abgeschlossen: {experiment.completed_at}")

        if experiment.parent_experiment_id:
            print(f"Parent Experiment: {experiment.parent_experiment_id}")

        if experiment.tags:
            print(f"Tags: {', '.join(experiment.tags)}")

        # Konfiguration
        print(f"\n--- Konfiguration ---")
        config = experiment.configuration
        print(f"Strategie: {config.strategy_name}")
        print(f"Timeframe: {config.timeframe}")
        print(f"Pairs: {', '.join(config.pairs[:5])}" + ("..." if len(config.pairs) > 5 else ""))
        print(f"Stake Amount: {config.stake_amount}")
        print(f"Max Open Trades: {config.max_open_trades}")
        print(f"Stoploss: {config.stoploss}")
        print(f"Config Hash: {config.configuration_hash}")

        # Metriken
        print(f"\n--- Metriken ---")
        metrics = experiment.metrics
        print(f"Total Trades: {metrics.total_trades}")
        print(f"Winning Trades: {metrics.winning_trades}")
        print(f"Losing Trades: {metrics.losing_trades}")
        print(f"Total Profit: {metrics.total_profit}")
        print(f"Profit Ratio: {metrics.profit_ratio:.4f}")
        print(f"Win Rate: {metrics.win_rate:.2%}")
        print(f"Avg Profit/Trade: {metrics.avg_profit_per_trade:.4f}")
        print(f"Max Drawdown: {metrics.max_drawdown:.4f}")

        if metrics.custom_metrics:
            print(f"Custom Metrics: {metrics.custom_metrics}")

        # Timeline
        if include_timeline:
            print(f"\n--- Timeline ---")
            timeline = self.tracker.get_experiment_timeline(experiment_id)
            for event in timeline[-10:]:  # Letzte 10 Events
                print(f"{event['timestamp']}: {event.get('message', event.get('progress_type', 'Unknown'))}")

        # Notizen
        if experiment.notes:
            print(f"\n--- Notizen ---")
            print(experiment.notes)

    def compare_experiments(self, experiment_ids: List[str], output_format: str = "table"):
        """Vergleicht mehrere Experimente"""

        comparison = self.tracker.compare_experiments(experiment_ids)

        if not comparison.get('experiments'):
            print("Keine gültigen Experimente für Vergleich gefunden.")
            return

        print(f"\n=== Experiment-Vergleich ===")

        # Vergleichstabelle
        data = []
        for exp in comparison['experiments']:
            data.append({
                'ID': exp['id'][:8],
                'Name': exp['name'][:20],
                'Status': exp['status'],
                'Trades': exp['metrics']['total_trades'],
                'Profit%': f"{exp['metrics']['profit_ratio']:.2%}",
                'Win Rate': f"{exp['metrics']['win_rate']:.2%}",
                'Max DD': f"{exp['metrics']['max_drawdown']:.2%}",
                'Duration (h)': f"{exp.get('duration', 0) / 3600:.1f}" if exp.get('duration') else "N/A"
            })

        self._output_data(data, output_format, "Experiment-Vergleich")

        # Beste Werte
        print(f"\n--- Beste Werte ---")
        for metric, best in comparison.get('best_by_metric', {}).items():
            print(f"{metric}: {best['value']:.4f} (Experiment: {best['experiment_id'][:8]})")

        # Zusammenfassung
        summary = comparison.get('summary', {})
        print(f"\n--- Zusammenfassung ---")
        print(f"Experimente insgesamt: {summary.get('total_experiments', 0)}")
        print(f"Abgeschlossen: {summary.get('completed', 0)}")
        print(f"Fehlgeschlagen: {summary.get('failed', 0)}")
        print(f"Durchschnittliche Profit Ratio: {summary.get('avg_profit_ratio', 0):.4f}")

    def export_experiment(self, experiment_id: str, output_path: Optional[str] = None):
        """Exportiert einen Experiment-Bericht"""

        if not output_path:
            output_path = f"experiment_{experiment_id}_report.json"

        output_file = Path(output_path)

        success = self.tracker.export_experiment_report(experiment_id, output_file)

        if success:
            print(f"Experiment-Bericht exportiert: {output_file}")
        else:
            print(f"Fehler beim Exportieren des Experiment-Berichts")

    def delete_experiment(self, experiment_id: str, confirm: bool = False):
        """Löscht ein Experiment"""

        if not confirm:
            response = input(f"Experiment {experiment_id} wirklich löschen? (y/N): ")
            if response.lower() != 'y':
                print("Löschung abgebrochen.")
                return

        # Implementierung des Löschens
        with self.tracker.get_db_connection() as conn:
            # Lösche Logs und Progress
            conn.execute("DELETE FROM experiment_logs WHERE experiment_id = ?", (experiment_id,))
            conn.execute("DELETE FROM experiment_progress WHERE experiment_id = ?", (experiment_id,))

            # Lösche Experiment
            cursor = conn.execute("DELETE FROM experiments WHERE experiment_id = ?", (experiment_id,))

            if cursor.rowcount > 0:
                conn.commit()
                print(f"Experiment {experiment_id} gelöscht.")
            else:
                print(f"Experiment {experiment_id} nicht gefunden.")

    def cleanup_experiments(self, days_old: int = 30, dry_run: bool = True):
        """Bereinigt alte Experimente"""

        if dry_run:
            print(f"Dry Run: Experimente älter als {days_old} Tage würden gelöscht werden.")
            # Zeige welche Experimente betroffen wären
            from datetime import datetime, timezone, timedelta
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

            with self.tracker.get_db_connection() as conn:
                cursor = conn.execute(
                    "SELECT experiment_id, name, created_at FROM experiments WHERE created_at < ?",
                    (cutoff_date.isoformat(),)
                )
                old_experiments = cursor.fetchall()

                if old_experiments:
                    print(f"\nBetroffene Experimente ({len(old_experiments)}):")
                    for exp in old_experiments:
                        print(f"  {exp['experiment_id'][:8]}: {exp['name']} ({exp['created_at']})")
                else:
                    print("Keine alten Experimente gefunden.")
        else:
            deleted_count = self.tracker.cleanup_old_experiments(days_old)
            print(f"{deleted_count} alte Experimente gelöscht.")

    def generate_dashboard(self, output_format: str = "json"):
        """Generiert ein Dashboard"""

        # Lade Dashboard-Daten
        config = {'user_data_dir': 'user_data'}
        integration = FreqtradeExperimentIntegration(config)
        dashboard = integration.generate_experiment_dashboard()

        if output_format == "json":
            print(json.dumps(dashboard, indent=2, default=str))
        else:
            print(f"\n=== Experiment Dashboard ===")

            # Zusammenfassung
            summary = dashboard['summary']
            print(f"\nÜbersicht:")
            print(f"  Experimente gesamt: {summary['total_experiments']}")
            print(f"  Aktiv: {summary['active_experiments']}")
            print(f"  Abgeschlossen: {summary['completed_experiments']}")
            print(f"  Fehlgeschlagen: {summary['failed_experiments']}")

            # Nach Typ
            print(f"\nNach Typ:")
            for exp_type, count in dashboard['by_type'].items():
                print(f"  {exp_type}: {count}")

            # Neueste Experimente
            if dashboard['recent_experiments']:
                print(f"\nNeueste Experimente:")
                for exp in dashboard['recent_experiments']:
                    print(f"  {exp['id'][:8]}: {exp['name']} ({exp['status']})")

            # Beste Performer
            if dashboard['best_performers']:
                print(f"\nBeste Performer:")
                for exp in dashboard['best_performers']:
                    print(f"  {exp['id'][:8]}: {exp['strategy']} (Profit: {exp['profit_ratio']:.2%})")

    def _output_data(self, data: List[Dict], output_format: str, title: str):
        """Hilfsfunktion für Datenausgabe"""

        if not data:
            print(f"Keine Daten für {title}")
            return

        if output_format == "json":
            print(json.dumps(data, indent=2, default=str))
        elif output_format == "csv":
            df = pd.DataFrame(data)
            print(df.to_csv(index=False))
        else:  # table
            print(f"\n{title}:")
            print(tabulate(data, headers="keys", tablefmt="grid"))


def main():
    """Hauptfunktion für CLI"""

    parser = argparse.ArgumentParser(description="Freqtrade Enhanced Persistence Tracker CLI")
    parser.add_argument("--db", type=str, help="Pfad zur Experiment-Datenbank")

    subparsers = parser.add_subparsers(dest="command", help="Verfügbare Kommandos")

    # List command
    list_parser = subparsers.add_parser("list", help="Liste Experimente")
    list_parser.add_argument("--type", choices=[t.value for t in ExperimentType], help="Filter nach Typ")
    list_parser.add_argument("--status", choices=[s.value for s in ExperimentStatus], help="Filter nach Status")
    list_parser.add_argument("--limit", type=int, default=50, help="Maximale Anzahl")
    list_parser.add_argument("--format", choices=["table", "json", "csv"], default="table", help="Ausgabeformat")

    # Show command
    show_parser = subparsers.add_parser("show", help="Zeige Experiment-Details")
    show_parser.add_argument("experiment_id", help="Experiment ID")
    show_parser.add_argument("--timeline", action="store_true", help="Zeige Timeline")

    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Vergleiche Experimente")
    compare_parser.add_argument("experiment_ids", nargs="+", help="Experiment IDs")
    compare_parser.add_argument("--format", choices=["table", "json"], default="table", help="Ausgabeformat")

    # Export command
    export_parser = subparsers.add_parser("export", help="Exportiere Experiment")
    export_parser.add_argument("experiment_id", help="Experiment ID")
    export_parser.add_argument("--output", help="Ausgabedatei")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Lösche Experiment")
    delete_parser.add_argument("experiment_id", help="Experiment ID")
    delete_parser.add_argument("--yes", action="store_true", help="Bestätigung überspringen")

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Bereinige alte Experimente")
    cleanup_parser.add_argument("--days", type=int, default=30, help="Alter in Tagen")
    cleanup_parser.add_argument("--dry-run", action="store_true", default=True, help="Nur anzeigen")
    cleanup_parser.add_argument("--execute", action="store_true", help="Tatsächlich löschen")

    # Dashboard command
    dashboard_parser = subparsers.add_parser("dashboard", help="Generiere Dashboard")
    dashboard_parser.add_argument("--format", choices=["json", "text"], default="text", help="Ausgabeformat")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialisiere CLI
    db_path = Path(args.db) if args.db else None
    cli = ExperimentCLI(db_path)

    # Führe Kommando aus
    try:
        if args.command == "list":
            cli.list_experiments(
                experiment_type=args.type,
                status=args.status,
                limit=args.limit,
                output_format=args.format
            )

        elif args.command == "show":
            cli.show_experiment(args.experiment_id, include_timeline=args.timeline)

        elif args.command == "compare":
            cli.compare_experiments(args.experiment_ids, output_format=args.format)

        elif args.command == "export":
            cli.export_experiment(args.experiment_id, args.output)

        elif args.command == "delete":
            cli.delete_experiment(args.experiment_id, confirm=args.yes)

        elif args.command == "cleanup":
            cli.cleanup_experiments(args.days, dry_run=not args.execute)

        elif args.command == "dashboard":
            cli.generate_dashboard(output_format=args.format)

    except Exception as e:
        print(f"Fehler beim Ausführen des Kommandos: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()