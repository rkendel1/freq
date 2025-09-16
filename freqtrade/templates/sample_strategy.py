# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these libs ---
import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Any, Union

from freqtrade.strategy import (
    BooleanParameter,
    CategoricalParameter,
    DecimalParameter,
    IntParameter,
    IStrategy,
    merge_informative_pair,
)

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class SampleStrategy(IStrategy):
    """
    Eine deutlich ausgefeiltere Beispiel-Strategie für Freqtrade.

    Ziele:
    - Maximale Gewinne bei gleichzeitig möglichst kleinen Verlusten
    - Robustere Einstiege durch Mehrfach-Bestätigung (Multi-Timeframe, Trend + Momentum + Volumen)
    - Dynamische Stops (Trailing + abgestufter Custom-Stoploss)
    - Telegram-Signale mit *klarer Herkunft* der Werte (aus den Spalten des DataFrames)

    WICHTIG: Diese Strategie ist ein technisches Beispiel, keine Finanzberatung.
    Backtesten, Forwardtesten und für die eigene Börse / Pairlist anpassen!
    """

    # --- Grundlegendes Interface ---
    INTERFACE_VERSION = 3

    # --- Zeithorizonte ---
    timeframe = "5m"  # Haupt-Timeframe
    informative_timeframe = "1h"  # Höherer Timeframe zur Trend-Bestätigung

    # --- ROI-Ziele in Stufen (Minuten -> minimaler Profit) ---
    #    Idee: Nimm früher kleine Gewinne, wenn das Setup nur kurz läuft,
    #    und lass Trades länger laufen, wenn sie gut performen.
    minimal_roi = {
        # Sofort nach Einstieg noch kein harter ROI-Zwang
        "0": 0.12,  # 12% wenn sehr schnell erreichbar (bei Futures mit Hebel üblich, bei Spot anpassen)
        "30": 0.06,  # Nach 30 Minuten: 6%
        "120": 0.035,  # Nach 2 Stunden: 3.5%
        "360": 0.02,  # Nach 6 Stunden: 2%
        "720": 0.01,  # Nach 12 Stunden: 1%
    }

    # --- Stoploss & Trailing ---
    # Fester Sicherheitsgurt (wird dynamisch über custom_stoploss nachgezogen)
    stoploss = -0.08  # -8%
    trailing_stop = True
    trailing_stop_positive = 0.012  # 1.2% Trailing wenn Offset erreicht
    trailing_stop_positive_offset = 0.055  # 5.5% im Gewinn, dann Trailing scharf stellen
    trailing_only_offset_is_reached = True

    # --- Short-Trading aktivieren (nur auf Derivaten/Futures nutzbar) ---
    can_short: bool = True

    # --- Sonstige Strategie-Parameter ---
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Für EMA200, ATR etc. brauchen wir genügend Historie
    startup_candle_count: int = 210

    # Order-Setup (ggf. an Exchange anpassen)
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }
    order_time_in_force = {"entry": "gtc", "exit": "gtc"}

    # --- Interne Helfer für Telegram-Deduplikation ---
    _last_signal_key_by_pair: dict[str, str] = {}

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        logger.info("🚀 Freqtrade Bot gestartet!")
        logger.info("📱 Telegram-Signale werden gesendet (sofern in der Config aktiviert).")
        logger.info(
            "⚡ Strategie: Multi-Timeframe Trend + Momentum + Volumen mit dynamischen Stops."
        )

    # --- Protections (optional, ergänzen je nach Bedarf) ---
    # Hinweis: Protections können auch in der globalen config.json liegen.
    # Hier nur konservative Defaults.
    def protections(self) -> list[dict[str, Any]]:
        return [
            # Kurze Abkühlphase nach jedem Trade
            {"method": "CooldownPeriod", "stop_duration_candles": 5},
            # Vermeide neue Einstiege bei zu vielen Stoplosses in kurzer Zeit
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 72,
                "trade_limit": 10,
                "stop_duration_candles": 72,
                "only_per_pair": False,
                "only_per_side": False,
                "stoploss": -0.08,
            },
            # Schutz bei größerem Drawdown
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 720,
                "trade_limit": 20,
                "stop_duration_candles": 120,
                "max_allowed_drawdown": 0.2,
            },
        ]

    def informative_pairs(self) -> list[tuple[str, str]]:
        """
        Zusätzliche (Pair, Timeframe)-Kombinationen, die wir für Filter/Bestätigungen zwischenspeichern.
        Hier: für alle Pairs aus der aktuellen Whitelist zusätzlich den 1h-Chart.
        """
        pairs = self.dp.current_whitelist() if self.dp else []
        return [(p, self.informative_timeframe) for p in pairs]

    # -----------------------------
    # Indikatoren
    # -----------------------------
    def _bollinger(self, df: DataFrame, period: int = 20, dev: float = 2.0) -> DataFrame:
        bb = ta.BBANDS(df, timeperiod=period, nbdevup=dev, nbdevdn=dev, matype=0)
        df["bb_lower"] = bb["lowerband"]
        df["bb_middle"] = bb["middleband"]
        df["bb_upper"] = bb["upperband"]
        return df

    @staticmethod
    def _crossed_above(series1: pd.Series, series2: pd.Series) -> pd.Series:
        return (series1 > series2) & (series1.shift(1) <= series2.shift(1))

    @staticmethod
    def _crossed_below(series1: pd.Series, series2: pd.Series) -> pd.Series:
        return (series1 < series2) & (series1.shift(1) >= series2.shift(1))

    @staticmethod
    def _rolling_vwap(df: DataFrame, window: int = 20) -> pd.Series:
        # Einfacher, gleitender VWAP auf Basis des Typical Price
        tp = (df["high"] + df["low"] + df["close"]) / 3.0
        vwap = (tp * df["volume"]).rolling(window=window, min_periods=1).sum() / df[
            "volume"
        ].rolling(window=window, min_periods=1).sum()
        return vwap

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Berechnet alle Indikatoren auf dem Haupt-Timeframe (5m) und
        mergen außerdem Bestätigungs-Indikatoren vom 1h-Chart.
        """

        # --- Haupt-Timeframe (5m) ---
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        macd = ta.MACD(dataframe)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macdhist"] = macd["macdhist"]

        dataframe["ema_20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_200"] = ta.EMA(dataframe, timeperiod=200)

        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)

        dataframe = self._bollinger(dataframe, period=20, dev=2.0)

        # Volumen-Filter (aktuelles Volumen vs. 20er Durchschnitt)
        dataframe["vol_ma20"] = dataframe["volume"].rolling(20).mean()
        dataframe["vol_ok"] = dataframe["volume"] > (dataframe["vol_ma20"] * 1.2)

        # Gleitender VWAP (20 Perioden)
        dataframe["vwap20"] = self._rolling_vwap(dataframe, window=20)

        # --- Informative Timeframe (1h) ---
        if self.dp:
            pair = metadata["pair"]
            informative = self.dp.get_pair_dataframe(
                pair=pair, timeframe=self.informative_timeframe
            )

            # Indikatoren auf 1h
            informative["rsi"] = ta.RSI(informative, timeperiod=14)
            informative["ema_50"] = ta.EMA(informative, timeperiod=50)
            informative["ema_200"] = ta.EMA(informative, timeperiod=200)
            macd_h = ta.MACD(informative)
            informative["macd"] = macd_h["macd"]
            informative["macdsignal"] = macd_h["macdsignal"]

            informative = self._bollinger(informative, period=20, dev=2.0)

            # Merge mit Suffix "_1h"
            dataframe = merge_informative_pair(
                base_dataframe=dataframe,
                informative_dataframe=informative,
                timeframe=self.timeframe,
                informative_timeframe=self.informative_timeframe,
                ffill=True,
            )

        # Sauberkeit: Keine NaNs am Anfang
        dataframe.fillna(method="ffill", inplace=True)
        dataframe.fillna(method="bfill", inplace=True)

        return dataframe

    # -----------------------------
    # Entry Signale
    # -----------------------------
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Einstiegssignale für Long & Short.
        Anforderungen:
          - Trendfilter über EMA200 (5m) + Bestätigung via 1h-EMA200
          - Momentum-Bestätigung via MACD-Kreuz
          - RSI-Extrembereiche (Überverkauft/Überkauft) ODER Bollinger-Touch
          - Volumen über Durchschnitt (Breakout-Charakter)
        """

        # --- Long: Trend nach oben + Momentum + Erschöpfung im RSI oder BB-Lower ---
        macd_cross_up = self._crossed_above(dataframe["macd"], dataframe["macdsignal"])
        long_trend = (dataframe["close"] > dataframe["ema_200"]) & (
            dataframe["ema_50"] > dataframe["ema_200"]
        )

        # Bestätigung auf 1h (nur wenn vorhanden)
        if "ema_200_1h" in dataframe:
            long_trend = long_trend & (dataframe["close_1h"] > dataframe["ema_200_1h"])

        long_momentum = macd_cross_up & (dataframe["adx"] > 18)
        long_exhaustion = (dataframe["rsi"] < 38) | (
            dataframe["close"] <= dataframe["bb_lower"] * 1.01
        )

        long_cond = long_trend & long_momentum & long_exhaustion & dataframe["vol_ok"]

        dataframe.loc[long_cond, "enter_long"] = 1
        dataframe.loc[long_cond, "enter_tag"] = "L:TrendUp+MACD↑+RSI/BBlow+Vol"

        # --- Short: Trend nach unten + Momentum + Erschöpfung im RSI oder BB-Upper ---
        macd_cross_dn = self._crossed_below(dataframe["macd"], dataframe["macdsignal"])
        short_trend = (dataframe["close"] < dataframe["ema_200"]) & (
            dataframe["ema_50"] < dataframe["ema_200"]
        )
        if "ema_200_1h" in dataframe:
            short_trend = short_trend & (dataframe["close_1h"] < dataframe["ema_200_1h"])

        short_momentum = macd_cross_dn & (dataframe["adx"] > 18)
        short_exhaustion = (dataframe["rsi"] > 62) | (
            dataframe["close"] >= dataframe["bb_upper"] * 0.99
        )

        short_cond = (
            short_trend & short_momentum & short_exhaustion & dataframe["vol_ok"] & self.can_short
        )

        dataframe.loc[short_cond, "enter_short"] = 1
        dataframe.loc[short_cond, "enter_tag"] = "S:TrendDn+MACD↓+RSI/BBup+Vol"

        # --- Telegram: Nur für die letzte Kerze und entdoppelt ---
        self._maybe_send_telegram_signal(dataframe, metadata, for_exit=False)

        return dataframe

    # -----------------------------
    # Exit Signale
    # -----------------------------
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit-Signale (ergänzen die ROI- und Stoploss-Logik):
          - Long: Schwächeanzeichen (MACD↓, RSI>70 zurück, Close<EMA20, BB-Upper-Touch)
          - Short: Umgekehrt
        """
        macd_cross_dn = self._crossed_below(dataframe["macd"], dataframe["macdsignal"])
        macd_cross_up = self._crossed_above(dataframe["macd"], dataframe["macdsignal"])

        # Long-Exit
        long_exit = (
            macd_cross_dn
            | (dataframe["rsi"] > 72)
            | (dataframe["close"] < dataframe["ema_20"])
            | (dataframe["close"] >= dataframe["bb_upper"] * 0.998)
        )
        dataframe.loc[long_exit, "exit_long"] = 1
        dataframe.loc[long_exit, "exit_tag"] = "L:Weakness(MACD↓/RSI/EMA20/BBupper)"

        # Short-Exit
        short_exit = (
            macd_cross_up
            | (dataframe["rsi"] < 28)
            | (dataframe["close"] > dataframe["ema_20"])
            | (dataframe["close"] <= dataframe["bb_lower"] * 1.002)
        )
        dataframe.loc[short_exit, "exit_short"] = 1
        dataframe.loc[short_exit, "exit_tag"] = "S:Weakness(MACD↑/RSI/EMA20/BBlower)"

        # Telegram
        self._maybe_send_telegram_signal(dataframe, metadata, for_exit=True)

        return dataframe

    # -----------------------------
    # Dynamischer Stoploss: Je mehr Profit, desto enger
    # -----------------------------
    def custom_stoploss(
        self,
        pair: str,
        trade: "Trade",
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> float:
        """
        Gibt den Stoploss (als negativer Prozentwert) dynamisch zurück.

        Idee:
        - Früh locker lassen, damit Trade atmen kann
        - Mit steigendem Profit schneller nachziehen
        - Ergänzt das globale Trailing-Stop-Setup
        """
        # Wenn stark im Gewinn, enger Stop
        if current_profit > 0.10:
            return -0.02  # max -2% Rücklauf toleriert
        if current_profit > 0.06:
            return -0.03
        if current_profit > 0.03:
            return -0.05
        # Anfangs großzügiger
        return self.stoploss

    # -----------------------------
    # Optional: Hebel für Futures/Derivate
    # -----------------------------
    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        side: str,
        **kwargs,
    ) -> float:
        """
        Konservative Default-Hebel. Passe ggf. auf Exchange-Limits an.
        """
        base = 2.0 if side == "long" else 2.0
        return float(min(base, max_leverage))

    # -----------------------------
    # Telegram-Helfer
    # -----------------------------
    def _maybe_send_telegram_signal(
        self, dataframe: DataFrame, metadata: dict, for_exit: bool
    ) -> None:
        """
        Sendet pro (Pair, Candle, Richtung, Typ) ein Signal in Telegram.
        - Werte stammen *direkt* aus den Spalten des DataFrames (siehe Formatierung unten).
        - Durch process_only_new_candles=True und unseren internen Schlüssel wird Doppel-Posting vermieden.
        """
        try:
            if not getattr(self, "dp", None):
                return
            if not self.config.get("telegram", {}).get("enabled", False):
                return
        except Exception:
            # In Backtests ist telegram meist deaktiviert – dann schweigen
            return

        if dataframe.empty:
            return

        last = dataframe.iloc[-1]
        pair = metadata.get("pair", "")
        ts = last.get("date", None)
        if isinstance(ts, pd.Timestamp):
            ts_str = ts.isoformat()
        else:
            ts_str = str(ts)

        side = (
            "EXIT"
            if for_exit
            else (
                "LONG"
                if int(last.get("enter_long", 0) or 0) == 1
                else ("SHORT" if int(last.get("enter_short", 0) or 0) == 1 else None)
            )
        )
        if not side:
            return

        key = f"{pair}:{self.timeframe}:{ts_str}:{side}"
        if self._last_signal_key_by_pair.get(pair) == key:
            return  # bereits gesendet

        price = float(last.get("close", 0.0))

        # Herkunft der Werte:
        # - RSI  -> last['rsi']
        # - MACD -> last['macd'] vs. last['macdsignal']
        # - Trend: last['close'] zu last['ema_200'] (5m) und optional last['close_1h'] zu last['ema_200_1h']
        # - Bollinger: last['bb_lower'], last['bb_upper']
        # - Volumen-Filter: last['vol_ok'] (bool)
        rsi = float(last.get("rsi", 0.0))
        macd = float(last.get("macd", 0.0))
        macdsig = float(last.get("macdsignal", 0.0))
        ema200 = float(last.get("ema_200", 0.0))
        ema200_1h = float(last.get("ema_200_1h", 0.0)) if "ema_200_1h" in last else None
        bb_l = float(last.get("bb_lower", 0.0))
        bb_u = float(last.get("bb_upper", 0.0))
        vol_ok = bool(last.get("vol_ok", False))

        parts = [
            f"{side} Signal {pair} {self.timeframe} @ {price:.6f}",
            f"RSI={rsi:.2f}",
            f"MACD={macd:.4f}/{macdsig:.4f}",
            f"EMA200(5m)={'über' if price > ema200 else 'unter'} {ema200:.6f}",
        ]
        if ema200_1h:
            parts.append(
                f"EMA200(1h)={'über' if last.get('close_1h', 0.0) > ema200_1h else 'unter'} {ema200_1h:.6f}"
            )
        parts.append(f"BB-L/U={bb_l:.6f}/{bb_u:.6f}")
        parts.append(f"VolOK={'Ja' if vol_ok else 'Nein'}")
        parts.append(f"Zeit={ts_str}")

        # Tag/Grund (kommt aus 'enter_tag' bzw. 'exit_tag' Spalten)
        tag_col = "exit_tag" if for_exit else "enter_tag"
        tag_val = str(last.get(tag_col, "") or "")
        if tag_val:
            parts.append(f"Grund={tag_val}")

        # Absenden
        try:
            self.dp.send_msg(" | ".join(parts))
            self._last_signal_key_by_pair[pair] = key
        except Exception as e:
            logger.warning(f"Telegram-Signal konnte nicht gesendet werden: {e}")
