#!/usr/bin/env python3
"""
🧬 ADAPTIVE EVOLUTION ENGINE - KONTINUIERLICHE STRATEGIE-VERBESSERUNG
Führt endlose Backtesting-Zyklen durch bis zur theoretischen Perfektion

EVOLUTION ZIEL: Erreiche unfehlbare lokale Minima-Erkennung durch:
- Kontinuierliche Parameter-Optimierung
- Multi-Generationen Genetische Algorithmen
- Adaptive Marktbedingungen
- Konvergenz-Überwachung
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import optimize
from sklearn.metrics import f1_score
import optuna

# Freqtrade imports
sys.path.insert(0, str(Path(__file__).parent))

from user_data.strategies.BinanceSpotLongOnlyRLStrategy_Enhanced import (
    BinanceSpotLongOnlyRLStrategy_Enhanced,
    LocalMinimaPredictor,
)

# Configure logging
logs_dir = Path('./logs')
logs_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/evolution.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EvolutionMetrics:
    """📊 Metriken für Evolution-Tracking"""

    def __init__(self):
        self.generation = 0
        self.best_f1_score = 0.0
        self.best_parameters = None
        self.improvement_history = []
        self.convergence_counter = 0
        self.total_backtests = 0
        self.evolution_start_time = datetime.now()

    def update_best(self, f1_score: float, parameters: Dict):
        if f1_score > self.best_f1_score:
            improvement = f1_score - self.best_f1_score
            self.best_f1_score = f1_score
            self.best_parameters = parameters.copy()
            self.improvement_history.append({
                'generation': self.generation,
                'improvement': improvement,
                'f1_score': f1_score,
                'parameters': parameters.copy(),
                'timestamp': datetime.now().isoformat()
            })
            self.convergence_counter = 0
            logger.info(f"🚀 NEW BEST F1-SCORE: {f1_score:.6f} (+{improvement:.6f})")
            return True
        else:
            self.convergence_counter += 1
            return False


class MarketScenarioGenerator:
    """🏭 Generiert diverse Marktszenarien für robuste Evolution"""

    @staticmethod
    def generate_complex_scenario(length: int = 300, seed: int = None) -> tuple[pd.DataFrame, List[int]]:
        """Generiert komplexe Marktszenarien mit bekannten Minima"""
        if seed is not None:
            np.random.seed(seed)

        # Extreme Diversität der Parameter
        base_price = np.random.uniform(20000, 100000)
        cycle_configs = []

        # Mehrere verschiedene Zyklustypen
        num_cycle_types = np.random.randint(3, 6)
        for _ in range(num_cycle_types):
            cycle_configs.append({
                'length': np.random.randint(10, 50),
                'amplitude': np.random.uniform(0.05, 0.25),
                'noise': np.random.uniform(0.01, 0.1),
                'trend': np.random.uniform(-0.3, 0.2),
                'min_position': np.random.uniform(0.3, 0.9)
            })

        start_date = datetime(2024, 10, 1)
        dates = [start_date + timedelta(minutes=5*i) for i in range(length)]

        prices = []
        true_minima_indices = []
        current_idx = 0

        while current_idx < length:
            # Zufälligen Zyklustyp wählen
            config = np.random.choice(cycle_configs)
            cycle_length = min(config['length'], length - current_idx)

            # Komplexe Wellenform mit überlagerten Frequenzen
            cycle_data = []
            for i in range(cycle_length):
                phase = 2 * np.pi * i / cycle_length

                # Grundwelle
                base_wave = np.sin(phase - np.pi * config['min_position'])

                # Harmonische Obertöne
                harmonic = 0.3 * np.sin(3 * phase) + 0.2 * np.sin(5 * phase)

                # Zufälliges Rauschen
                noise = np.random.normal(0, config['noise'])

                value = config['amplitude'] * (base_wave + 0.3 * harmonic) + noise
                cycle_data.append(value)

                # Minimum bei konfigurierter Position
                if abs(i - int(config['min_position'] * cycle_length)) <= 1:
                    true_minima_indices.append(current_idx + i)

            prices.extend(cycle_data)
            current_idx += cycle_length

        # Finaler Trend und Skalierung
        trend = np.linspace(0, np.random.uniform(-0.2, 0.1), len(prices))
        final_prices = base_price * (1 + np.array(prices) + trend)

        # DataFrame erstellen
        df = pd.DataFrame({
            'date': dates[:len(final_prices)],
            'open': final_prices * (1 + np.random.normal(0, 0.001, len(final_prices))),
            'high': final_prices * (1 + np.abs(np.random.normal(0, 0.003, len(final_prices)))),
            'low': final_prices * (1 - np.abs(np.random.normal(0, 0.003, len(final_prices)))),
            'close': final_prices,
            'volume': np.random.lognormal(15, 0.5, len(final_prices))
        })

        df.set_index('date', inplace=True)

        # Bereinige Minima-Indices
        true_minima_indices = [idx for idx in true_minima_indices if idx < len(df)]

        return df, true_minima_indices


class EvolutionEngine:
    """🧬 Hauptevolutions-Engine für kontinuierliche Verbesserung"""

    def __init__(self):
        self.metrics = EvolutionMetrics()
        self.scenario_generator = MarketScenarioGenerator()
        self.improvement_threshold = float(os.getenv('IMPROVEMENT_THRESHOLD', 0.001))
        self.convergence_patience = int(os.getenv('CONVERGENCE_PATIENCE', 50))
        self.max_generations = int(os.getenv('EVOLUTION_CYCLES', 20))  # Reduziert für Test

        # Erstelle Ausgabeverzeichnisse
        Path('./adaptive_evolution_results').mkdir(exist_ok=True)
        Path('./logs').mkdir(exist_ok=True)

    def objective_function(self, trial):
        """Optuna Objective-Funktion für Hyperparameter-Optimierung"""

        # Parameter-Bereiche definieren
        proximity_threshold = trial.suggest_float('proximity_threshold', 0.01, 0.99)
        confidence_threshold = trial.suggest_float('confidence_threshold', 0.01, 0.99)
        lookback_period = trial.suggest_int('lookback_period', 5, 50)
        window_size = trial.suggest_int('window_size', 3, 15)

        parameters = {
            'proximity_threshold': proximity_threshold,
            'confidence_threshold': confidence_threshold,
            'lookback_period': lookback_period,
            'window_size': window_size
        }

        # Teste auf mehreren Szenarien
        total_f1 = 0.0
        scenarios_tested = 0

        for scenario_seed in range(5):  # 5 verschiedene Marktszenarien
            try:
                # Generiere Marktszenario
                data, true_minima = self.scenario_generator.generate_complex_scenario(
                    length=np.random.randint(200, 400),
                    seed=scenario_seed + self.metrics.generation * 100
                )

                # Teste Parameter
                f1_score = self.evaluate_parameters(parameters, data, true_minima)
                total_f1 += f1_score
                scenarios_tested += 1

            except Exception as e:
                logger.warning(f"Scenario {scenario_seed} failed: {e}")
                continue

        # Durchschnittliche Performance
        avg_f1 = total_f1 / scenarios_tested if scenarios_tested > 0 else 0.0
        self.metrics.total_backtests += scenarios_tested

        return avg_f1

    def evaluate_parameters(self, parameters: Dict, data: pd.DataFrame, true_minima: List[int]) -> float:
        """Evaluiert Parameter-Set auf gegebenen Daten"""

        try:
            # Strategie konfigurieren
            config = {"timeframe": "5m", "stake_currency": "USDT"}
            strategy = BinanceSpotLongOnlyRLStrategy_Enhanced(config)

            # Parameter setzen
            strategy.minima_proximity_threshold.value = parameters['proximity_threshold']
            strategy.minima_confidence_threshold.value = parameters['confidence_threshold']

            # Indikatoren berechnen
            metadata = {'pair': 'BTC/USDT'}
            df_indicators = strategy.populate_indicators(data.copy(), metadata)

            # Minima vorhersagen
            predictor = LocalMinimaPredictor(
                window_size=parameters.get('window_size', 5),
                lookback_periods=parameters['lookback_period']
            )
            predicted_minima = predictor.find_local_minima(df_indicators['close'].values)

            # F1-Score berechnen
            tolerance = 10
            if not predicted_minima or not true_minima:
                return 0.0

            # True Positives
            true_positives = sum(1 for pred in predicted_minima
                               if any(abs(pred - true) <= tolerance for true in true_minima))

            # Precision und Recall
            precision = true_positives / len(predicted_minima) if predicted_minima else 0
            recall = true_positives / len(true_minima) if true_minima else 0

            # F1-Score
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

            return f1

        except Exception as e:
            logger.error(f"Parameter evaluation failed: {e}")
            return 0.0

    def run_evolution_cycle(self):
        """Führt einen Evolution-Zyklus durch"""

        logger.info(f"🧬 STARTING EVOLUTION GENERATION {self.metrics.generation}")

        # Optuna Study für diese Generation
        study = optuna.create_study(direction='maximize')
        study.optimize(self.objective_function, n_trials=5)  # Reduziert für schnelleren Test

        # Beste Parameter dieser Generation
        best_params = study.best_params
        best_f1 = study.best_value

        logger.info(f"Generation {self.metrics.generation} - Best F1: {best_f1:.6f}")
        logger.info(f"Best Parameters: {best_params}")

        # Update Metriken
        improved = self.metrics.update_best(best_f1, best_params)

        # Speichere Ergebnisse
        self.save_generation_results(best_params, best_f1, study.trials)

        self.metrics.generation += 1

        return improved

    def save_generation_results(self, best_params: Dict, best_f1: float, trials):
        """Speichert Generations-Ergebnisse"""

        results = {
            'generation': self.metrics.generation,
            'best_f1_score': best_f1,
            'best_parameters': best_params,
            'all_time_best_f1': self.metrics.best_f1_score,
            'all_time_best_parameters': self.metrics.best_parameters,
            'total_backtests': self.metrics.total_backtests,
            'convergence_counter': self.metrics.convergence_counter,
            'evolution_runtime_hours': (datetime.now() - self.metrics.evolution_start_time).total_seconds() / 3600,
            'trials': [{'params': trial.params, 'value': trial.value} for trial in trials],
            'timestamp': datetime.now().isoformat()
        }

        # Speichere Generation
        gen_file = f'./adaptive_evolution_results/generation_{self.metrics.generation:04d}.json'
        with open(gen_file, 'w') as f:
            json.dump(results, f, indent=2)

        # Update globales Best
        best_file = './adaptive_evolution_results/best_ever.json'
        with open(best_file, 'w') as f:
            json.dump({
                'best_f1_score': self.metrics.best_f1_score,
                'best_parameters': self.metrics.best_parameters,
                'improvement_history': self.metrics.improvement_history,
                'total_generations': self.metrics.generation,
                'total_backtests': self.metrics.total_backtests
            }, f, indent=2)

    def check_convergence(self) -> bool:
        """Prüft ob Evolution konvergiert ist"""

        if self.metrics.convergence_counter >= self.convergence_patience:
            logger.info(f"🎯 CONVERGENCE REACHED after {self.metrics.generation} generations")
            logger.info(f"Best F1-Score: {self.metrics.best_f1_score:.6f}")
            return True

        if self.metrics.best_f1_score >= 0.999:
            logger.info(f"🏆 NEAR-PERFECT SCORE ACHIEVED: {self.metrics.best_f1_score:.6f}")
            return True

        return False

    def run_infinite_evolution(self):
        """Führt kontinuierliche Evolution bis zur Konvergenz durch"""

        logger.info("🚀 STARTING INFINITE EVOLUTION SYSTEM")
        logger.info(f"Target: {self.max_generations} generations or convergence")
        logger.info(f"Improvement threshold: {self.improvement_threshold}")
        logger.info(f"Convergence patience: {self.convergence_patience}")

        try:
            while self.metrics.generation < self.max_generations:

                # Evolution-Zyklus
                improved = self.run_evolution_cycle()

                # Status-Update
                logger.info(f"Generation {self.metrics.generation} complete")
                logger.info(f"Best ever F1: {self.metrics.best_f1_score:.6f}")
                logger.info(f"Convergence counter: {self.metrics.convergence_counter}/{self.convergence_patience}")

                # Konvergenz-Check
                if self.check_convergence():
                    break

                # Kurze Pause zwischen Generationen
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Evolution stopped by user")
        except Exception as e:
            logger.error(f"Evolution error: {e}")
        finally:
            logger.info("🎉 EVOLUTION COMPLETE")
            logger.info(f"Final best F1-Score: {self.metrics.best_f1_score:.6f}")
            logger.info(f"Total generations: {self.metrics.generation}")
            logger.info(f"Total backtests: {self.metrics.total_backtests}")


if __name__ == "__main__":

    # Initialisiere Evolution Engine
    engine = EvolutionEngine()

    # Starte unendliche Evolution
    engine.run_infinite_evolution()