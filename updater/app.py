#!/usr/bin/env python3

import schedule
import asyncio
import aiohttp
import time
import redis
import os
import queue
import logging
from logging.handlers import QueueListener, QueueHandler
from logging import StreamHandler
import sys
from json import dumps as json_dump


SECRET_FILE = "/run/secrets/keys"
with open(SECRET_FILE, "r") as file:
    SECRET = file.readline().strip()


COINS_FILE = "/coin_list"
COINS = []
with open(COINS_FILE, "r") as file:
    COINS = [f.strip() for f in file.readlines()]


COINGLASS_DICT = {
    "funding_rates_u": ("https://open-api.coinglass.com/api/pro/v1/futures/"
                        "funding_rates_chart?symbol={symbol}&type=U"),
    "funding_rates_c": ("https://open-api.coinglass.com/api/pro/v1/futures/"
                        "funding_rates_chart?symbol={symbol}&type=C"),
    "open_interest": ("http://open-api.coinglass.com/api/pro/v1/futures/"
                      "openInterest?interval=0&symbol={symbol}")
 }

COINGECKO_URL = ("https://api.coingecko.com/api/v3/coins"
                 "/markets?vs_currency=usd"
                 "&order=market_cap_desc"
                 "&per_page=250&page={page}&sparkline=false")


if "REFRESH_RATE" in os.environ:
    REFRESH_RATE = int(os.environ["REFRESH_RATE"])
else:
    REFRESH_RATE = 3600


if "CONCURRENT_REQUESTS" in os.environ:
    CONCURRENT_REQUESTS = int(os.environ["CONCURRENT_REQUESTS"])
else:
    CONCURRENT_REQUESTS = 10


if "INTER_REQUEST_TIME" in os.environ:
    INTER_REQUEST_TIME = int(os.environ["INTER_REQUEST_TIME"])
else:
    INTER_REQUEST_TIME = 3


async def _coinglassRequests(rtype, symbol):
    """
    Make a request to the coinglass api.

    The type of the request (funding_rates_u, funding_rates_c or openInterest)
    is given by RTYPE and the coin to fetch is given by SYMBOL
    """
    headers = {"coinglassSecret": SECRET}
    async with aiohttp.ClientSession() as session:
        url = COINGLASS_DICT[rtype].format(symbol=symbol)
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                logging.getLogger(__name__).info(
                    "Coinglass request made for {url}".format(url=url))
                return (symbol, await response.text())
            else:
                logging.getLogger(__name__).error(
                    "request to {url} returned code {code}"
                    .format(url=url, code=response.status))
                raise Exception(("the request for symbol {symbol}"
                                 " received a status"
                                 " code {code}").format(symbol=symbol,
                                                        code=response.status))


async def _coingeckoRequests(page):
    async with aiohttp.ClientSession() as session:
        url = COINGECKO_URL.format(page=page)
        async with session.get(url) as response:
            if response.status == 200:
                logging.getLogger(__name__).info(
                    "Coingecko request made for {url}".format(url=url))
                return await response.json()
            else:
                logging.getLogger(__name__).error(
                    "request to {url} returned code {code}"
                    .format(url=url, code=response.status))
                raise Exception(("the request for page {page}"
                                 " received a status"
                                 " code {code}").format(page=page,
                                                        code=response.status))


async def _coinglass_runner(rtype, redis):

    async def inner(requests):
        results = await asyncio.gather(*requests)
        redis.mset({
            f"{rtype}.{coin}": body
            for (coin, body) in results
        })

    for coin_set in [COINS[x:x+CONCURRENT_REQUESTS]
                     if x < len(COINS)-CONCURRENT_REQUESTS
                     else COINS[x:]
                     for x in range(0, len(COINS), CONCURRENT_REQUESTS)]:
        await inner([_coinglassRequests(rtype, coin) for coin in coin_set])
        await asyncio.sleep(INTER_REQUEST_TIME)


async def _coingecko_runner(redis):
    coingecko_results = await asyncio.gather(*[_coingeckoRequests(p)
                                               for p in range(1, 7)])
    redis.mset({
        f"coingecko.{element['symbol'].upper()}": json_dump(element)
        for body in coingecko_results
        for element in body
    })


def main(r):
    asyncio.run(_coingecko_runner(r))
    logging.getLogger(__name__).info("Finished the set of coingecko requests")
    for rtype in COINGLASS_DICT.keys():
        asyncio.run(_coinglass_runner(rtype, r))
        logging.getLogger(__name__).info(
            "Finished the set of Coinglass requests"
            "for type {rtype}".format(rtype=rtype))

log_queue = queue.Queue()
queue_handler = QueueHandler(log_queue)
logging.basicConfig(level=logging.INFO)
logging.getLogger().addHandler(queue_handler)
stream_handler = StreamHandler(sys.stdout)
queue_listener = QueueListener(log_queue,
                               stream_handler)
queue_listener.start()
r = redis.Redis(host='redis',
                port=6379)
main(r)
schedule.every(REFRESH_RATE).seconds.do(main, r)
while(True):
    schedule.run_pending()
    time.sleep(1)
