#!/usr/bin/env python3
"""
🔍 DEBUG: ANALYSE WARUM KEINE ENTRY-SIGNALE GENERIERT WERDEN
Detaillierte Analyse der Entry-Bedingungen mit realen Daten
"""

import sys
from pathlib import Path

import pandas as pd


# Freqtrade imports
sys.path.insert(0, str(Path(__file__).parent))

from user_data.strategies.BinanceSpotLongOnlyRLStrategy_Enhanced import (
    BinanceSpotLongOnlyRLStrategy_Enhanced,
)


def load_real_data():
    """
    📊 LÄDT ECHTE MARKTDATEN VON BINANCE
    """
    # BTC/USDT Daten von 2024-10-01
    data_path = Path("user_data/data/binance/BTC_USDT-5m.json")

    if data_path.exists():
        print(f"✅ Lade echte Daten von: {data_path}")
        df = pd.read_json(data_path)

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)

        print(f"📊 Daten geladen: {len(df)} Kerzen")
        print(f"📅 Zeitraum: {df.index.min()} bis {df.index.max()}")
        print(f"💰 Preisspanne: {df['close'].min():.2f} - {df['close'].max():.2f}")

        return df
    else:
        print(f"❌ Datei nicht gefunden: {data_path}")
        return None


def debug_entry_conditions():
    """
    🔍 DEBUGGT ENTRY-BEDINGUNGEN SCHRITT FÜR SCHRITT
    """
    print("🔍 DEBUG: ANALYSE DER ENTRY-BEDINGUNGEN")
    print("=" * 50)

    # 1. Lade echte Daten
    data = load_real_data()
    if data is None:
        print("❌ Keine Daten verfügbar für Analyse")
        return

    # 2. Initialisiere Strategie
    config = {"timeframe": "5m", "stake_currency": "USDT"}
    strategy = BinanceSpotLongOnlyRLStrategy_Enhanced(config)
    metadata = {"pair": "BTC/USDT"}

    print("\n📋 AKTUELLE PARAMETER:")
    print(f"   🎯 Proximity Threshold: {strategy.minima_proximity_threshold.value}")
    print(f"   📊 Confidence Threshold: {strategy.minima_confidence_threshold.value}")
    print(f"   📈 RSI Oversold: {strategy.rsi_oversold.value}")
    print(f"   📊 Volume Threshold: {strategy.volume_threshold.value}")

    # 3. Berechne Indikatoren
    print("\n🔄 Berechne Indikatoren...")
    try:
        df_indicators = strategy.populate_indicators(data.copy(), metadata)
        print(f"✅ Indikatoren berechnet für {len(df_indicators)} Kerzen")

        # 4. Analysiere Indikator-Werte
        print("\n📊 INDIKATOR-ANALYSE:")

        # RSI Analyse
        rsi_valid = df_indicators["rsi"].dropna()
        rsi_count = len(rsi_valid)
        rsi_oversold_count = (rsi_valid < strategy.rsi_oversold.value).sum()

        print("   📈 RSI:")
        print(f"      • Gültige Werte: {rsi_count}")
        print(f"      • Bereich: {rsi_valid.min():.1f} - {rsi_valid.max():.1f}")
        print(f"      • Oversold (< {strategy.rsi_oversold.value}): {rsi_oversold_count} Kerzen")
        print(f"      • Beispiel RSI-Werte: {rsi_valid.tail(5).tolist()}")

        # Proximity Analyse
        proximity_valid = df_indicators["minima_proximity"].dropna()
        proximity_count = len(proximity_valid)
        proximity_above_count = (proximity_valid > strategy.minima_proximity_threshold.value).sum()

        print("   🎯 Minima Proximity:")
        print(f"      • Gültige Werte: {proximity_count}")
        print(f"      • Bereich: {proximity_valid.min():.3f} - {proximity_valid.max():.3f}")
        print(
            f"      • Über Threshold (> {strategy.minima_proximity_threshold.value}): {proximity_above_count} Kerzen"
        )
        print(f"      • Beispiel Proximity-Werte: {proximity_valid.tail(5).round(3).tolist()}")

        # Confidence Analyse
        confidence_valid = df_indicators["minima_confidence"].dropna()
        confidence_count = len(confidence_valid)
        confidence_above_count = (
            confidence_valid > strategy.minima_confidence_threshold.value
        ).sum()

        print("   📊 Minima Confidence:")
        print(f"      • Gültige Werte: {confidence_count}")
        print(f"      • Bereich: {confidence_valid.min():.3f} - {confidence_valid.max():.3f}")
        print(
            f"      • Über Threshold (> {strategy.minima_confidence_threshold.value}): {confidence_above_count} Kerzen"
        )
        print(f"      • Beispiel Confidence-Werte: {confidence_valid.tail(5).round(3).tolist()}")

        # 5. Kombinierte Bedingungen
        print("\n🔄 KOMBINIERTE BEDINGUNGEN:")

        rsi_condition = df_indicators["rsi"] < strategy.rsi_oversold.value
        proximity_condition = (
            df_indicators["minima_proximity"] > strategy.minima_proximity_threshold.value
        )
        confidence_condition = (
            df_indicators["minima_confidence"] > strategy.minima_confidence_threshold.value
        )

        combined = rsi_condition & proximity_condition & confidence_condition
        combined_count = combined.fillna(False).sum()

        print(
            f"   ✅ RSI < {strategy.rsi_oversold.value}: {rsi_condition.fillna(False).sum()} Kerzen"
        )
        print(
            f"   ✅ Proximity > {strategy.minima_proximity_threshold.value}: {proximity_condition.fillna(False).sum()} Kerzen"
        )
        print(
            f"   ✅ Confidence > {strategy.minima_confidence_threshold.value}: {confidence_condition.fillna(False).sum()} Kerzen"
        )
        print(f"   🎯 ALLE BEDINGUNGEN: {combined_count} Kerzen")

        # 6. Entry Trend Analyse
        print("\n🚀 ENTRY TREND BERECHNUNG:")
        df_with_entry = strategy.populate_entry_trend(df_indicators, metadata)

        entry_signals = df_with_entry["enter_long"].fillna(0).sum()
        print(f"   📈 Entry Signale: {int(entry_signals)}")

        if entry_signals > 0:
            entry_points = df_with_entry[df_with_entry["enter_long"] == 1]
            print("   🎉 ENTRY SIGNALE GEFUNDEN:")

            for i, (idx, row) in enumerate(entry_points.iterrows()):
                print(f"      Signal {i + 1}: {idx}")
                print(f"         💰 Preis: {row['close']:.2f}")
                print(f"         📈 RSI: {row['rsi']:.1f}")
                print(f"         🎯 Proximity: {row['minima_proximity']:.3f}")
                print(f"         📊 Confidence: {row['minima_confidence']:.3f}")
                print(f"         💪 Entry Strength: {row['adaptive_entry_strength']:.3f}")
        else:
            print("   ❌ KEINE ENTRY SIGNALE")

            # Zeige letzte 5 Kerzen mit Details
            print("\n🔍 LETZTE 5 KERZEN DETAILS:")
            last_5 = df_with_entry.tail(5)

            for i, (idx, row) in enumerate(last_5.iterrows()):
                print(f"      Kerze {i + 1}: {idx}")
                print(f"         💰 Preis: {row['close']:.2f}")
                print(
                    f"         📈 RSI: {row['rsi']:.1f} (< {strategy.rsi_oversold.value}: {row['rsi'] < strategy.rsi_oversold.value})"
                )
                print(
                    f"         🎯 Proximity: {row['minima_proximity']:.3f} (> {strategy.minima_proximity_threshold.value}: {row['minima_proximity'] > strategy.minima_proximity_threshold.value})"
                )
                print(
                    f"         📊 Confidence: {row['minima_confidence']:.3f} (> {strategy.minima_confidence_threshold.value}: {row['minima_confidence'] > strategy.minima_confidence_threshold.value})"
                )
                print(f"         💪 Entry Strength: {row['adaptive_entry_strength']:.3f}")
                print(f"         🚀 Enter Long: {row.get('enter_long', 'N/A')}")

        return entry_signals > 0

    except Exception as e:
        print(f"❌ Fehler bei Indikator-Berechnung: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 DEBUG-ANALYSE DER LOKALEN MINIMA STRATEGIE")
    print("=" * 60)
    print("ZIEL: Verstehen warum keine Entry-Signale generiert werden")
    print("-" * 60)

    success = debug_entry_conditions()

    print(f"\n{'=' * 60}")
    if success:
        print("✅ DEBUG ERFOLGREICH - Entry-Signale gefunden!")
        print("Das System funktioniert und generiert Buy-In Positionen!")
    else:
        print("🔍 DEBUG ABGESCHLOSSEN - Detaillierte Analyse gezeigt")
        print("Alle Bedingungen und Parameter wurden analysiert")
        print("")
        print("💡 LÖSUNGSANSÄTZE:")
        print("1. Parameter weiter reduzieren (Proximity < 0.01)")
        print("2. RSI Threshold erhöhen (> 80)")
        print("3. Mehr historische Daten verwenden")
        print("4. Entry-Logik vereinfachen")

    print("\n📊 Die Analyse zeigt die exakten Werte aller Indikatoren")
    print("und warum Entry-Signale generiert werden oder nicht!")
