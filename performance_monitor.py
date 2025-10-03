#!/usr/bin/env python3
"""
📊 PERFORMANCE MONITOR - ÜBERWACHUNG DER EVOLUTION
Kontinuierliches Monitoring der Strategie-Evolution in Echtzeit
"""

import json
import time
import logging
import os
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EvolutionMonitor:
    """📊 Überwacht Evolution-Performance"""

    def __init__(self):
        self.monitoring_interval = int(os.getenv('MONITORING_INTERVAL', 60))
        self.results_dir = Path('/freqtrade/adaptive_evolution_results')
        self.logs_dir = Path('/freqtrade/logs')

    def get_latest_metrics(self):
        """Lädt neueste Evolution-Metriken"""
        try:
            best_file = self.results_dir / 'best_ever.json'
            if best_file.exists():
                with open(best_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Error reading metrics: {e}")
            return None

    def create_evolution_plot(self, metrics):
        """Erstellt Evolution-Visualisierung"""
        try:
            if not metrics or 'improvement_history' not in metrics:
                return

            history = metrics['improvement_history']
            if not history:
                return

            # Daten extrahieren
            generations = [h['generation'] for h in history]
            f1_scores = [h['f1_score'] for h in history]
            improvements = [h['improvement'] for h in history]

            # Plot erstellen
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

            # F1-Score Evolution
            ax1.plot(generations, f1_scores, 'b-o', linewidth=2, markersize=4)
            ax1.set_title('F1-Score Evolution über Generationen', fontweight='bold')
            ax1.set_xlabel('Generation')
            ax1.set_ylabel('F1-Score')
            ax1.grid(True, alpha=0.3)
            ax1.set_ylim(0, 1)

            # Verbesserungen pro Generation
            ax2.bar(generations, improvements, alpha=0.7, color='green')
            ax2.set_title('Verbesserungen pro Generation', fontweight='bold')
            ax2.set_xlabel('Generation')
            ax2.set_ylabel('F1-Score Verbesserung')
            ax2.grid(True, alpha=0.3)

            # Kumulative Verbesserung
            cumulative = [sum(improvements[:i+1]) for i in range(len(improvements))]
            ax3.plot(generations, cumulative, 'r-s', linewidth=2, markersize=4)
            ax3.set_title('Kumulative Verbesserung', fontweight='bold')
            ax3.set_xlabel('Generation')
            ax3.set_ylabel('Kumulative F1-Score Verbesserung')
            ax3.grid(True, alpha=0.3)

            # Performance Statistiken
            current_f1 = metrics.get('best_f1_score', 0)
            total_gens = metrics.get('total_generations', 0)
            total_tests = metrics.get('total_backtests', 0)

            stats_text = f"""
            EVOLUTION STATISTIKEN

            Beste F1-Score: {current_f1:.6f}
            Generationen: {total_gens}
            Backtests: {total_tests}

            Perfektion: {current_f1*100:.3f}%
            Verbleibend: {(1-current_f1)*100:.3f}%
            """

            ax4.text(0.1, 0.5, stats_text, fontsize=12, verticalalignment='center',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue"))
            ax4.set_xlim(0, 1)
            ax4.set_ylim(0, 1)
            ax4.axis('off')
            ax4.set_title('Aktuelle Statistiken', fontweight='bold')

            plt.tight_layout()
            plt.savefig(self.results_dir / 'evolution_progress.png', dpi=300, bbox_inches='tight')
            plt.close()

            logger.info("📊 Evolution plot updated")

        except Exception as e:
            logger.error(f"Error creating plot: {e}")

    def log_status(self, metrics):
        """Loggt aktuellen Status"""
        if not metrics:
            logger.info("🔍 No evolution metrics available yet")
            return

        current_f1 = metrics.get('best_f1_score', 0)
        total_gens = metrics.get('total_generations', 0)
        total_tests = metrics.get('total_backtests', 0)

        # Berechne Perfektion
        perfection_percent = current_f1 * 100
        remaining_percent = (1 - current_f1) * 100

        logger.info("📊 EVOLUTION STATUS:")
        logger.info(f"   🎯 Best F1-Score: {current_f1:.6f} ({perfection_percent:.3f}%)")
        logger.info(f"   🧬 Generationen: {total_gens}")
        logger.info(f"   🔬 Backtests: {total_tests}")
        logger.info(f"   ⚡ Verbesserungspotential: {remaining_percent:.3f}%")

        # Konvergenz-Warnung
        if current_f1 >= 0.999:
            logger.info("🏆 NEAR-PERFECT PERFORMANCE ACHIEVED!")
        elif current_f1 >= 0.99:
            logger.info("🚀 EXCELLENT PERFORMANCE - APPROACHING PERFECTION")
        elif current_f1 >= 0.95:
            logger.info("✅ VERY GOOD PERFORMANCE")
        elif current_f1 >= 0.9:
            logger.info("📈 GOOD PERFORMANCE")
        else:
            logger.info("🔧 OPTIMIZATION IN PROGRESS")

    def monitor_evolution(self):
        """Hauptmonitor-Loop"""
        logger.info("📊 STARTING EVOLUTION MONITOR")
        logger.info(f"Monitoring interval: {self.monitoring_interval}s")

        while True:
            try:
                # Lade Metriken
                metrics = self.get_latest_metrics()

                # Status loggen
                self.log_status(metrics)

                # Visualisierung erstellen
                if metrics:
                    self.create_evolution_plot(metrics)

                # Warten bis nächstes Update
                time.sleep(self.monitoring_interval)

            except KeyboardInterrupt:
                logger.info("Monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(10)


if __name__ == "__main__":
    monitor = EvolutionMonitor()
    monitor.monitor_evolution()