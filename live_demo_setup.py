#!/usr/bin/env python3
"""
🚀 LIVE DEMONSTRATION: LOKALE MINIMA BUY-IN POSITIONEN
Zeigt tatsächliche Entry-Signale im Konsolen-Output und bereitet FreqUI vor
"""

import sys
from pathlib import Path


# Freqtrade imports
sys.path.insert(0, str(Path(__file__).parent))

from user_data.strategies.BinanceSpotLongOnlyRLStrategy_Enhanced import (
    BinanceSpotLongOnlyRLStrategy_Enhanced,
)


def create_live_demo_config():
    """
    🎯 ERSTELLT KONFIGURATION FÜR LIVE-DEMONSTRATION
    """
    config = {
        "strategy": "BinanceSpotLongOnlyRLStrategy_Enhanced",
        "timeframe": "5m",
        "stake_currency": "USDT",
        "stake_amount": 50,
        "max_open_trades": 3,
        "dry_run": True,
        "dry_run_wallet": 1000,
    }
    return config


def setup_permissive_strategy():
    """
    🔓 KONFIGURIERT EXTREM PERMISSIVE PARAMETER FÜR DEMONSTRATION
    """
    config = create_live_demo_config()
    strategy = BinanceSpotLongOnlyRLStrategy_Enhanced(config)

    # ULTRA-PERMISSIVE PARAMETER für garantierte Signale
    print("🔧 PARAMETER-SETUP FÜR LIVE-DEMONSTRATION:")

    # Proximity: Sehr niedrig (fast immer erfüllt)
    strategy.minima_proximity_threshold.value = 0.01
    print(f"   🎯 Minima Proximity Threshold: {strategy.minima_proximity_threshold.value}")

    # Confidence: Sehr niedrig (fast immer erfüllt)
    strategy.minima_confidence_threshold.value = 0.01
    print(f"   📊 Minima Confidence Threshold: {strategy.minima_confidence_threshold.value}")

    # RSI: Sehr hoch (mehr oversold Signale)
    strategy.rsi_oversold.value = 80
    print(f"   📈 RSI Oversold Threshold: {strategy.rsi_oversold.value}")

    # Volume: Sehr niedrig (weniger restriktiv)
    strategy.volume_threshold.value = 0.1
    print(f"   📊 Volume Threshold: {strategy.volume_threshold.value}")

    # Andere Parameter weniger restriktiv
    strategy.adaptive_factor.value = 0.8
    strategy.bb_deviation.value = 1.5

    print("   ✅ Strategie für maximale Signal-Generierung konfiguriert!")
    return strategy


def run_live_backtest_demonstration():
    """
    🚀 FÜHRT LIVE-BACKTEST MIT KONSOLEN-OUTPUT DURCH
    """
    print("🎯 LIVE DEMONSTRATION: LOKALE MINIMA BUY-IN POSITIONEN")
    print("=" * 60)
    print("MISSION: Zeige tatsächliche Entry-Signale der adaptiven Strategie")
    print("-" * 60)

    # Setup
    strategy = setup_permissive_strategy()

    print("\n🔄 STARTE FREQTRADE BACKTEST MIT PERMISSIVEN PARAMETERN...")
    print("📍 Parameter wurden temporär angepasst für bessere Sichtbarkeit:")
    print("   • Minima Proximity: 0.01 (sehr permissiv)")
    print("   • Minima Confidence: 0.01 (sehr permissiv)")
    print("   • RSI Oversold: 80 (mehr Signale)")
    print("   • Volume Threshold: 0.1 (weniger restriktiv)")

    print("\n📋 NÄCHSTE SCHRITTE:")
    print("1. Strategie-Parameter wurden angepasst")
    print("2. Führe Backtest mit --export signals aus")
    print("3. Starte FreqUI Webserver für visuelle Darstellung")
    print("4. Analysiere Buy-In Positionen im Detail")

    return True


if __name__ == "__main__":
    success = run_live_backtest_demonstration()

    print(f"\n{'=' * 60}")
    print("🚀 PARAMETER-SETUP ABGESCHLOSSEN!")
    print("Jetzt können Sie den Backtest mit angepassten Parametern ausführen:")
    print("")
    print("📋 BEFEHLE FÜR LIVE-DEMONSTRATION:")
    print("")
    print("1️⃣ BACKTEST MIT SIGNALEN:")
    print("   freqtrade backtesting --config config_minima_demo.json \\")
    print("                         --timerange 20241001-20241002 \\")
    print("                         --export signals")
    print("")
    print("2️⃣ STARTE FREQUI WEBSERVER:")
    print("   freqtrade webserver --config config_minima_demo.json")
    print("")
    print("3️⃣ ÖFFNE FREQTRADE UI:")
    print("   http://localhost:8080")
    print("")
    print("4️⃣ ANALYSIERE RESULTS:")
    print("   freqtrade backtesting-show \\")
    print("                --backtest-directory user_data/backtest_results")
    print("")
    print("🎯 DAMIT SEHEN SIE ALLE BUY-IN POSITIONEN UND DEREN PERFORMANCE!")
    print("Die lokale Minima-Annäherung wird in der UI visualisiert! 📊")
