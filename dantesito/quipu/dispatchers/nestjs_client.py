# dantesito/quipu/dispatchers/nestjs_client.py

import asyncio
import logging
from typing import Final

import httpx

from dantesito.quipu.config.schemas import CreateExpedienteDto
from dantesito.quipu.config.settings import QuipuSettings

logger = logging.getLogger("quipu_logger")
_MAX_ATTEMPTS: Final[int] = 3


class NestJSClient:
    def __init__(self, settings: QuipuSettings) -> None:
        self.settings = settings

    async def send_expediente(self, dto: CreateExpedienteDto) -> bool:
        endpoint = f"{self.settings.NESTJS_API_URL}/api/v1/expedientes"

        async with httpx.AsyncClient() as client:
            for intento in range(_MAX_ATTEMPTS):
                try:
                    response = await client.post(
                        endpoint,
                        json=dto.model_dump(),
                    )

                    if response.status_code == 201:
                        logger.info(
                            "Expediente %s transmitido correctamente a NestJS.",
                            dto.id_expediente_global,
                        )
                        return True

                    if 500 <= response.status_code <= 599:
                        raise httpx.HTTPStatusError(
                            f"NestJS respondió con HTTP {response.status_code}.",
                            request=response.request,
                            response=response,
                        )

                    logger.error(
                        "Error no recuperable al transmitir el expediente %s: "
                        "NestJS respondió con HTTP %s.",
                        dto.id_expediente_global,
                        response.status_code,
                    )
                    return False

                except (
                    httpx.ConnectError,
                    httpx.TimeoutException,
                    httpx.HTTPStatusError,
                ) as exc:
                    if intento == _MAX_ATTEMPTS - 1:
                        logger.critical(
                            "Transmisión del expediente %s agotada tras %d "
                            "intentos: %s",
                            dto.id_expediente_global,
                            _MAX_ATTEMPTS,
                            exc,
                        )
                        return False

                    backoff = 2 ** intento

                    logger.warning(
                        "Intento %d/%d fallido para el expediente %s: %s. "
                        "Reintentando en %d segundos.",
                        intento + 1,
                        _MAX_ATTEMPTS,
                        dto.id_expediente_global,
                        exc,
                        backoff,
                    )

                    await asyncio.sleep(backoff)

        return False