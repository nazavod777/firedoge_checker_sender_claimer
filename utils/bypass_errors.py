import asyncio.exceptions

import aiohttp.client_exceptions
from web3.exceptions import ContractLogicError

from utils import logger


async def bypass_errors(target_function,
                        **kwargs) -> any:
    try:
        return await target_function(**kwargs)

    except (asyncio.exceptions.TimeoutError, TimeoutError, aiohttp.client_exceptions.ClientResponseError):
        return await bypass_errors(target_function=target_function,
                                   **kwargs)

    except (ContractLogicError, ValueError, TypeError) as error:
        logger.error(f'Estimate Gas Error: {error}')
        return

    except Exception as error:
        logger.error(f'Unexpected Error: {error}')
        return
