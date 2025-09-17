# Telegram Setup für Freqtrade

## 1. Telegram Bot erstellen

1. Öffne Telegram und suche nach `@BotFather`
2. Starte eine Unterhaltung: `/start`
3. Erstelle einen neuen Bot: `/newbot`
4. Wähle einen Namen für deinen Bot (z.B. "Mein Trading Bot")
5. Wähle einen Username (muss auf "_bot" enden, z.B. "mein_trading_bot")
6. **Speichere den Token!** (z.B. `1234567890:ABCdefGhIJKlmNOPqrsTUVwxyZ`)

## 2. Chat-ID herausfinden

### Methode 1: Über API
1. Sende eine beliebige Nachricht an deinen Bot
2. Öffne im Browser: `https://api.telegram.org/bot<DEIN_TOKEN>/getUpdates`
3. Ersetze `<DEIN_TOKEN>` mit dem Token von BotFather
4. Suche in der JSON-Antwort nach `"chat":{"id":XXXXXXX}`
5. Die Nummer ist deine Chat-ID

### Methode 2: Über @userinfobot
1. Sende `/start` an `@userinfobot`
2. Deine Chat-ID wird angezeigt

## 3. Konfiguration aktualisieren

Bearbeite `/workspaces/freqtrade/user_data/config.json`:

```json
"telegram": {
    "enabled": true,
    "token": "HIER_DEIN_TOKEN_EINFÜGEN",
    "chat_id": "HIER_DEINE_CHAT_ID_EINFÜGEN"
}
```

**Beispiel:**
```json
"telegram": {
    "enabled": true,
    "token": "1234567890:ABCdefGhIJKlmNOPqrsTUVwxyZ",
    "chat_id": "123456789"
}
```

## 4. Bot neu starten

Nach der Konfiguration den Bot neu starten:
```bash
# Bot stoppen (Ctrl+C)
# Dann neu starten:
freqtrade trade --dry-run
```

## 5. Test

Sende `/status` an deinen Bot - er sollte antworten!

## Verfügbare Telegram-Befehle

- `/status` - Aktueller Status
- `/profit` - Gewinn/Verlust
- `/balance` - Kontostand
- `/trades` - Offene Trades
- `/performance` - Performance-Übersicht
- `/start` - Bot starten
- `/stop` - Bot stoppen
- `/help` - Hilfe anzeigen

## Fehlerbehebung

- Stelle sicher, dass der Token korrekt ist (keine Leerzeichen)
- Chat-ID muss eine Zahl sein (negative Zahlen für Gruppen)
- Bot muss eine Nachricht von dir erhalten haben, bevor er dir schreiben kann