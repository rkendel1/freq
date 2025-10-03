#!/usr/bin/env python3
"""
Simple Telegram Bot Test Script
"""

import os

import requests


def test_telegram_bot():
    token = os.getenv("TELEGRAM_TOKEN", "7970774758:AAFzBwa-33l0hNtD6We9kom7lmXHjUVfTPE")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "7480009116")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": "🤖 FreqTrade Adaptive RL Bot - Connection Test\n✅ Telegram Bot is working!",
    }

    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print("✅ Telegram test message sent successfully!")
            return True
        else:
            print(f"❌ Failed to send message: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    test_telegram_bot()
