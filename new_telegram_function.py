    def _maybe_send_telegram_signal(
        self, dataframe: DataFrame, metadata: dict, for_exit: bool
    ) -> None:
        """
        Sendet strukturierte Trading-Signale in Telegram nach dem gewünschten Format:
        1. Long oder Short
        2. Währungspaar
        3. Einstiegspunkt
        4. Stop-Loss
        5. Take-Profit
        6. Rendite
        7. Begründung
        """
        try:
            if not getattr(self, "dp", None):
                return
            if not self.config.get("telegram", {}).get("enabled", False):
                return
        except Exception:
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

        # Sichere Behandlung von NaN-Werten
        enter_long_val = last.get("enter_long", 0)
        enter_short_val = last.get("enter_short", 0)

        enter_long_safe = 0 if pd.isna(enter_long_val) else int(enter_long_val or 0)
        enter_short_safe = 0 if pd.isna(enter_short_val) else int(enter_short_val or 0)

        side = (
            "EXIT"
            if for_exit
            else ("LONG" if enter_long_safe == 1 else ("SHORT" if enter_short_safe == 1 else None))
        )
        if not side:
            return

        key = f"{pair}:{self.timeframe}:{ts_str}:{side}"
        if self._last_signal_key_by_pair.get(pair) == key:
            return

        price = float(last.get("close", 0.0))

        # Hol alle notwendigen Indikatoren
        rsi = float(last.get("rsi", 50.0))
        macd = float(last.get("macd", 0.0))
        macdsig = float(last.get("macdsignal", 0.0))
        ema200 = float(last.get("ema_200", price))
        bb_l = float(last.get("bb_lower", price * 0.95))
        bb_u = float(last.get("bb_upper", price * 1.05))
        vol_ok = bool(last.get("vol_ok", False))
        atr_value = float(last.get("atr", 0.0))

        # Tag/Grund
        tag_col = "exit_tag" if for_exit else "enter_tag"
        tag_val = str(last.get(tag_col, "") or "Kein Tag")

        if side in ["LONG", "SHORT"]:
            # ENTRY-SIGNAL nach gewünschter Struktur
            entry_conditions = self._get_precise_entry_conditions(last, side)
            optimal_entry = entry_conditions["optimal_entry"]

            stop_loss = self._calculate_stop_loss(optimal_entry, side, atr_value)
            take_profit = self._calculate_take_profit(optimal_entry, side, atr_value)

            # Berechne Rendite-Potenzial
            profit_potential = abs((take_profit - optimal_entry) / optimal_entry * 100)

            # Risk/Reward
            risk = abs(optimal_entry - stop_loss)
            reward = abs(take_profit - optimal_entry)
            rr_ratio = reward / risk if risk > 0 else 0

            message = (
                f"🚨 TRADING SIGNAL 🚨\n"
                f"\n**1. RICHTUNG:** {side} {'📈' if side == 'LONG' else '📉'}\n"
                f"**2. WÄHRUNGSPAAR:** {pair}\n"
                f"**3. EINSTIEGSPUNKT:** {optimal_entry:.6f}\n"
                f"**4. STOP-LOSS:** {stop_loss:.6f} ({abs((stop_loss-optimal_entry)/optimal_entry*100):.1f}%)\n"
                f"**5. TAKE-PROFIT:** {take_profit:.6f} ({profit_potential:.1f}%)\n"
                f"**6. RENDITE-POTENZIAL:** +{profit_potential:.1f}% (RR: 1:{rr_ratio:.1f})\n"
                f"**7. BEGRÜNDUNG:** {tag_val}\n"
                f"\n📊 **ZUSATZ-INFO:**\n"
                f"   • RSI: {rsi:.1f} {'(Überverkauft)' if rsi < 30 else '(Überkauft)' if rsi > 70 else '(Neutral)'}\n"
                f"   • MACD: {'Bullish' if macd > macdsig else 'Bearish'}\n"
                f"   • Trend: {'Aufwärts' if price > ema200 else 'Abwärts'}\n"
                f"   • Volumen: {'Stark' if vol_ok else 'Schwach'}\n"
                f"\n⏰ **ZEIT:** {ts_str}"
            )

        elif side == "EXIT":
            # EXIT-SIGNAL
            message = (
                f"🚪 EXIT SIGNAL 🚪\n"
                f"\n**1. RICHTUNG:** Position schließen\n"
                f"**2. WÄHRUNGSPAAR:** {pair}\n"
                f"**3. AUSSTIEGSPUNKT:** {price:.6f}\n"
                f"**4. GRUND:** {tag_val}\n"
                f"\n📊 **MARKTLAGE:**\n"
                f"   • RSI: {rsi:.1f} {'(Überverkauft)' if rsi < 30 else '(Überkauft)' if rsi > 70 else '(Neutral)'}\n"
                f"   • MACD: {'Bullish' if macd > macdsig else 'Bearish'}\n"
                f"   • Trend: {'Aufwärts' if price > ema200 else 'Abwärts'}\n"
                f"\n⏰ **ZEIT:** {ts_str}"
            )

        else:
            return

        # Signal senden
        try:
            self.dp.send_msg(message)
            self._last_signal_key_by_pair[pair] = key
        except Exception as e:
            self.logger.warning(f"Telegram-Signal konnte nicht gesendet werden: {e}")