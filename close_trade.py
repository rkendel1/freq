#!/usr/bin/env python3
"""
Script zum Schließen des offenen Trades in der SQLite-Datenbank
"""
import sqlite3
from datetime import datetime

def close_open_trades():
    """Schließt alle offenen Trades in der Datenbank"""
    conn = sqlite3.connect('/workspaces/freqtrade/tradesv3.dryrun.sqlite')
    cursor = conn.cursor()

    # Finde offene Trades
    cursor.execute("SELECT id, pair, is_short, amount, open_rate FROM trades WHERE is_open = 1")
    open_trades = cursor.fetchall()

    print(f"Gefundene offene Trades: {len(open_trades)}")

    for trade in open_trades:
        trade_id, pair, is_short, amount, open_rate = trade
        print(f"Trade {trade_id}: {pair} ({'SHORT' if is_short else 'LONG'}) - {amount} @ {open_rate}")

        # Schließe den Trade mit aktuellem Preis (simuliert)
        close_rate = open_rate * 0.999  # Kleiner Verlust
        close_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute("""
            UPDATE trades
            SET is_open = 0,
                close_rate = ?,
                close_date = ?,
                close_profit = -0.001,
                close_profit_abs = ?
            WHERE id = ?
        """, (close_rate, close_date, -amount * 0.001, trade_id))

        print(f"  → Trade {trade_id} geschlossen bei {close_rate}")

    conn.commit()
    conn.close()
    print("Alle Trades wurden geschlossen!")

if __name__ == "__main__":
    close_open_trades()