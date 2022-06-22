#!/usr/bin/env python3

from enum import Enum
from typing import Union
from fastapi import FastAPI, Query
import aioredis
import asyncio
from json import loads as loadJSON, JSONDecodeError


COINS_FILE = "/coin_list"
COINS = []
with open(COINS_FILE, "r") as file:
    COINS = {f.strip(): f.strip() for f in file.readlines()}

Coins = Enum("Coins", COINS)

REDIS_URL = "redis://redis"


class CoinglassOperation(str, Enum):
    funding_rates_u = "funding_rates_u"
    funding_rates_c = "funding_rates_c"
    open_interest = "open_interest"


async def redis_requests(prefix: str, keys: list = None):
    redis = aioredis.from_url(REDIS_URL)
    #TODO use mget instead of get
    if keys is None:
        keys = await redis.keys(pattern=f'{prefix}.*')
        requests = [redis.get(key) for key in keys]
    else:
        requests = [redis.get(f"{prefix}.{key}") for key in keys]
    responses = await asyncio.gather(*requests)
    result = []
    for resp in responses:
        try:
            result.append(loadJSON(resp))
        except (JSONDecodeError, TypeError):
            # TODO manage the exception
            pass
    return result


async def redis_single_request(prefix: str, key):
    redis = aioredis.from_url(REDIS_URL)
    k = f"{prefix}.{key}"
    print(k, flush=True)
    response = await redis.get(k)
    try:
        return loadJSON(response)
    except (JSONDecodeError, TypeError):
        # TODO manage the exception
        return None


frontend = FastAPI()


@frontend.get("/coinglass/{operation}")
async def coinglass(operation: CoinglassOperation, coin: Union[Coins, None] = None):
    if coin is None:
        return await redis_requests(operation.name, COINS)
    else:
        return await redis_single_request(operation.name, coin.name)


@frontend.get("/coingecko")
async def coingecko(id = None):
    redis_key_prefix = "coingecko"
    if id is None:
        return await redis_requests(redis_key_prefix)
    else:
        return await redis_single_request(redis_key_prefix, id)