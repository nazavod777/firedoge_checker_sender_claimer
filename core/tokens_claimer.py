import asyncio

import aiohttp
import web3.main
from pyuseragents import random as random_useragent
from web3 import Web3
from web3.auto import w3
from web3.eth import AsyncEth
from web3.types import TxParams

import settings.config
from utils import bypass_errors
from utils import get_address
from utils import get_gwei, get_nonce, get_chain_id
from utils import logger
from utils import read_abi

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,'
              '*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'accept-language': 'ru,en;q=0.9,vi;q=0.8,es;q=0.7,cy;q=0.6'
}


class TokensClaimer:
    def __init__(self,
                 private_key: str,
                 address: str):
        self.claim_contract = None
        self.config_json: dict | None = None
        self.provider: web3.main.Web3 | None = None
        self.address: str = address
        self.private_key: str = private_key

    async def get_transaction_data(self) -> tuple[str, int] | None:
        while True:
            try:
                async with aiohttp.ClientSession(headers={
                    **headers,
                    'user-agent': random_useragent()
                }) as session:
                    r = await bypass_errors(target_function=session.get,
                                            url=f'https://firedoge.fun/signs/{self.address[:4].lower()}.json')

                    if self.address.lower() in [current_address.lower() for current_address
                                                in list((await r.json()).keys())]:
                        for current_address, current_data in (await r.json()).items():
                            if current_address.lower() == self.address.lower():
                                return current_data['sign'], int(current_data['nonce'])

                    return

            except Exception as error:
                logger.error(f'{self.address} | {self.private_key} - Unexpected Error: {error}')

    async def send_transaction(self,
                               site_nonce: str,
                               site_signature: str) -> None:
        tasks: list = [get_nonce(provider=self.provider,
                                 address=self.address),
                       get_chain_id(provider=self.provider)]

        nonce, chain_id = await asyncio.gather(*tasks)

        gwei: float = w3.from_wei(number=await get_gwei(provider=self.provider),
                                  unit='gwei') if self.config_json['GWEI_CLAIM'] == 'auto' \
            else float(self.config_json['GWEI_CLAIM'])

        if self.config_json['GAS_LIMIT_CLAIM'] == 'auto':
            transaction_data: dict = {
                'chainId': chain_id,
                'gasPrice': w3.to_wei(gwei, 'gwei'),
                'from': self.address,
                'nonce': nonce,
                'value': 0
            }

            gas_limit: int | None = await bypass_errors(self.claim_contract.functions.claim(
                int(site_nonce),
                str(site_signature),
                '0x5D5ef29DE4dc277653742249095eD814C21CCc75'
            ).estimate_gas,
                                                        transaction=transaction_data)

        else:
            gas_limit: int = int(self.config_json['GAS_LIMIT_CLAIM'])

        if not gas_limit:
            return

        transaction_data: dict = {
            'chainId': chain_id,
            'gasPrice': w3.to_wei(gwei, 'gwei'),
            'from': self.address,
            'nonce': nonce,
            'value': 0,
            'gas': gas_limit
        }

        transaction: TxParams = await bypass_errors(self.claim_contract.functions.claim(
            int(site_nonce),
            str(site_signature),
            '0x5D5ef29DE4dc277653742249095eD814C21CCc75'
        ).build_transaction,
                                                    transaction=transaction_data)

        signed_transaction = self.provider.eth.account.sign_transaction(transaction_dict=transaction,
                                                                        private_key=self.private_key)

        await bypass_errors(target_function=self.provider.eth.send_raw_transaction,
                            transaction=signed_transaction.rawTransaction)

        transaction_hash: str = w3.to_hex(w3.keccak(signed_transaction.rawTransaction))
        logger.info(f'{self.address} | {self.private_key} - {transaction_hash}')

    async def start_work(self) -> None:
        self.config_json: dict = settings.config.config
        self.provider: web3.main.Web3 = Web3(Web3.AsyncHTTPProvider(self.config_json['RPC_URL']),
                                             modules={'eth': (AsyncEth,)},
                                             middlewares=[])
        self.claim_contract = self.provider.eth.contract(
            address=w3.to_checksum_address(value=self.config_json['CLAIM_CONTRACT_ADDRESS']),
            abi=await read_abi(filename='claim_abi.json'))
        transaction_data_response: tuple[str, int] | None = await self.get_transaction_data()

        if transaction_data_response:
            await self.send_transaction(site_nonce=transaction_data_response[1],
                                        site_signature=transaction_data_response[0])


def tokens_claimer(private_key: str) -> None:
    address: str = get_address(private_key=private_key)

    asyncio.run(TokensClaimer(private_key=private_key,
                              address=address).start_work())
