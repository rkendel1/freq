#!/usr/bin/env python3
"""
🏭 MARKET DATA GENERATOR - KONTINUIERLICHE MARKTDATEN-GENERIERUNG
Erzeugt kontinuierlich neue, diverse Marktszenarien für Evolution-Testing
"""

import json
import time
import logging
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContinuousMarketGenerator:
    """🏭 Kontinuierlicher Marktdaten-Generator"""

    def __init__(self):
        self.generation_interval = int(os.getenv('DATA_GENERATION_INTERVAL', 300))
        self.market_scenarios = int(os.getenv('MARKET_SCENARIOS', 10))
        self.data_dir = Path('/freqtrade/user_data/data')
        self.scenarios_dir = Path('/freqtrade/adaptive_evolution_results/scenarios')

        # Erstelle Verzeichnisse
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.scenarios_dir.mkdir(parents=True, exist_ok=True)

    def generate_extreme_market_conditions(self, scenario_id: int):
        """Generiert extreme Marktbedingungen für robustes Testing"""

        np.random.seed(scenario_id + int(time.time()))

        # Extreme Parameter-Ranges
        scenarios = {
            'bull_market': {
                'trend': np.random.uniform(0.1, 0.5),
                'volatility': np.random.uniform(0.02, 0.08),
                'cycle_irregularity': np.random.uniform(0.1, 0.3)
            },
            'bear_market': {
                'trend': np.random.uniform(-0.5, -0.1),
                'volatility': np.random.uniform(0.03, 0.12),
                'cycle_irregularity': np.random.uniform(0.2, 0.5)
            },
            'sideways_choppy': {
                'trend': np.random.uniform(-0.05, 0.05),
                'volatility': np.random.uniform(0.05, 0.15),
                'cycle_irregularity': np.random.uniform(0.3, 0.7)
            },
            'flash_crash': {
                'trend': np.random.uniform(-0.3, 0.1),
                'volatility': np.random.uniform(0.1, 0.25),
                'cycle_irregularity': np.random.uniform(0.5, 0.9)
            },
            'parabolic_rise': {
                'trend': np.random.uniform(0.2, 0.8),
                'volatility': np.random.uniform(0.02, 0.1),
                'cycle_irregularity': np.random.uniform(0.1, 0.4)
            }
        }

        # Zufälliges Szenario wählen
        scenario_type = np.random.choice(list(scenarios.keys()))
        params = scenarios[scenario_type]

        # Marktdaten generieren
        length = np.random.randint(200, 500)
        base_price = np.random.uniform(25000, 75000)

        # Komplexe Zyklen mit variabler Länge
        cycles = []
        current_pos = 0
        minima_positions = []

        while current_pos < length:
            cycle_length = max(10, int(np.random.normal(25, 10)))
            if current_pos + cycle_length > length:
                cycle_length = length - current_pos

            # Zyklusform mit Irregularitäten
            base_cycle = np.sin(np.linspace(0, 2*np.pi, cycle_length))

            # Irregularitäten hinzufügen
            irregularity = params['cycle_irregularity']
            for i in range(cycle_length):
                if np.random.random() < irregularity:
                    base_cycle[i] += np.random.normal(0, 0.3)

            cycles.extend(base_cycle)

            # Minimum-Position in diesem Zyklus
            min_idx = np.argmin(base_cycle)
            minima_positions.append(current_pos + min_idx)

            current_pos += cycle_length

        # Trend und Volatilität anwenden
        cycles = np.array(cycles[:length])
        trend_line = np.linspace(0, params['trend'], length)
        volatility_noise = np.random.normal(0, params['volatility'], length)

        # Finale Preise
        price_changes = 0.1 * (cycles + trend_line + volatility_noise)
        final_prices = base_price * np.cumprod(1 + price_changes)

        # DataFrame erstellen
        start_date = datetime.now() - timedelta(hours=length//12)  # 5min Kerzen
        dates = [start_date + timedelta(minutes=5*i) for i in range(length)]

        df = pd.DataFrame({
            'date': dates,
            'open': final_prices * (1 + np.random.normal(0, 0.001, length)),
            'high': final_prices * (1 + np.abs(np.random.normal(0, 0.003, length))),
            'low': final_prices * (1 - np.abs(np.random.normal(0, 0.003, length))),
            'close': final_prices,
            'volume': np.random.lognormal(15, 0.5, length)
        })

        df.set_index('date', inplace=True)

        # Minima bereinigen
        minima_positions = [pos for pos in minima_positions if 0 <= pos < length]

        # Szenario-Metadaten
        scenario_meta = {
            'scenario_id': scenario_id,
            'scenario_type': scenario_type,
            'parameters': params,
            'length': length,
            'base_price': base_price,
            'true_minima_count': len(minima_positions),
            'true_minima_positions': minima_positions,
            'generation_timestamp': datetime.now().isoformat()
        }

        return df, minima_positions, scenario_meta

    def save_scenario(self, scenario_id: int, df: pd.DataFrame, minima: list, meta: dict):
        """Speichert Marktszenario"""

        # Daten speichern
        data_file = self.scenarios_dir / f'market_scenario_{scenario_id:04d}.json'

        scenario_data = {
            'metadata': meta,
            'ohlcv_data': df.reset_index().to_dict(orient='records'),
            'true_minima': minima
        }

        with open(data_file, 'w') as f:
            json.dump(scenario_data, f, indent=2, default=str)

        logger.info(f"💾 Saved scenario {scenario_id}: {meta['scenario_type']} "
                   f"({meta['length']} candles, {len(minima)} minima)")

    def generate_scenario_batch(self):
        """Generiert Batch von Marktszenarien"""

        logger.info(f"🏭 Generating {self.market_scenarios} market scenarios...")

        scenario_batch = []

        for i in range(self.market_scenarios):
            try:
                scenario_id = int(time.time() * 1000) + i  # Eindeutige ID

                df, minima, meta = self.generate_extreme_market_conditions(scenario_id)
                self.save_scenario(scenario_id, df, minima, meta)

                scenario_batch.append({
                    'id': scenario_id,
                    'type': meta['scenario_type'],
                    'minima_count': len(minima)
                })

            except Exception as e:
                logger.error(f"Error generating scenario {i}: {e}")

        # Batch-Zusammenfassung speichern
        batch_summary = {
            'batch_timestamp': datetime.now().isoformat(),
            'scenarios_generated': len(scenario_batch),
            'scenarios': scenario_batch
        }

        summary_file = self.scenarios_dir / f'batch_summary_{int(time.time())}.json'
        with open(summary_file, 'w') as f:
            json.dump(batch_summary, f, indent=2)

        logger.info(f"✅ Generated {len(scenario_batch)} scenarios successfully")

        return scenario_batch

    def continuous_generation(self):
        """Kontinuierliche Szenario-Generierung"""

        logger.info("🏭 STARTING CONTINUOUS MARKET DATA GENERATION")
        logger.info(f"Generation interval: {self.generation_interval}s")
        logger.info(f"Scenarios per batch: {self.market_scenarios}")

        batch_counter = 0

        while True:
            try:
                batch_counter += 1
                logger.info(f"🏭 BATCH {batch_counter} - Generating new market scenarios...")

                # Generiere Szenarien
                scenarios = self.generate_scenario_batch()

                # Statistiken loggen
                scenario_types = {}
                for scenario in scenarios:
                    stype = scenario['type']
                    scenario_types[stype] = scenario_types.get(stype, 0) + 1

                logger.info("📊 Batch statistics:")
                for stype, count in scenario_types.items():
                    logger.info(f"   {stype}: {count} scenarios")

                # Warten bis nächste Generation
                logger.info(f"⏰ Waiting {self.generation_interval}s until next batch...")
                time.sleep(self.generation_interval)

            except KeyboardInterrupt:
                logger.info("Data generation stopped by user")
                break
            except Exception as e:
                logger.error(f"Data generation error: {e}")
                time.sleep(30)


if __name__ == "__main__":
    generator = ContinuousMarketGenerator()
    generator.continuous_generation()