# -*- coding: utf-8 -*-
"""
@Time ： 2025/1/23 下午1:51
@Author ： Jinbo CHEN
@File ：twitest.py
"""

import asyncio
from twikit import Client

USERNAME = 'cjb1234567'
EMAIL = 'chenjinbo123@gmail.com'
PASSWORD = 'chen.123'

# Initialize client
client = Client('en-US')


async def main():
    await client.login(
        auth_info_1=USERNAME,
        auth_info_2=EMAIL,
        password=PASSWORD
    )

    tweets = await client.search_tweet('elon musk', 'Latest')
    for tweet in tweets:
        print(tweet.text, tweet.reply_count, tweet.retweet_count,  tweet.quote_count, tweet.favorite_count, tweet.view_count)

    more_tweets = await tweets.next()

asyncio.run(main())




