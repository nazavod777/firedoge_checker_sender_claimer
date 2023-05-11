import asyncio

import aiofiles
import aiohttp
import web3.main
from pyuseragents import random as random_useragent

import settings.config
from utils import bypass_errors
from utils import get_address
from utils import logger

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,'
              '*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'accept-language': 'ru,en;q=0.9,vi;q=0.8,es;q=0.7,cy;q=0.6'
}


class EligibleChecker:
    def __init__(self,
                 private_key: str,
                 address: str):
        self.config_json: dict | None = None
        self.provider: web3.main.Web3 | None = None
        self.address: str = address
        self.private_key: str = private_key

    async def start_work(self) -> None:
        self.config_json: dict = settings.config.config

        async with aiohttp.ClientSession(headers={
            **headers,
            'user-agent': random_useragent()
        }) as session:
            while True:
                try:
                    r = await bypass_errors(target_function=session.get,
                                            url=f'https://firedoge.fun/signs/{self.address[:4].lower()}.json')

                    if self.address.lower() in [current_address.lower() for current_address
                                                in list((await r.json()).keys())]:
                        logger.success(f'{self.private_key} | Eligible')

                        async with aiofiles.open('eligible_checker_result/eligible.txt', 'a',
                                                 encoding='utf-8-sig') as f:
                            await f.write(f'{self.private_key}\n')

                    else:
                        logger.error(f'{self.private_key} | Not Eligible')

                        async with aiofiles.open('eligible_checker_result/not_eligible.txt', 'a',
                                                 encoding='utf-8-sig') as f:
                            await f.write(f'{self.private_key}\n')

                except Exception as error:
                    logger.error(f'{self.address} | {self.private_key} - Unexpected Error: {error}')

                else:
                    return


def eligible_checker(private_key: str) -> None:
    address: str = get_address(private_key=private_key)

    asyncio.run(EligibleChecker(private_key=private_key,
                                address=address).start_work())
