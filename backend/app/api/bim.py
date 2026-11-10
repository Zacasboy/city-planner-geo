"""Rotas da API de quantidades BIM/IFC (T2.4)."""

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool

from backend.app.services import bim_service
from backend.app.services.bim_models import BimQuantitiesResponse

router = APIRouter()

MAX_IFC_BYTES = 25 * 1024 * 1024


async def _read_body(request: Request) -> bytes:
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > MAX_IFC_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, detail="IFC file too large")
    body = b""
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_IFC_BYTES:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, detail="IFC file too large")
    return body


@router.post("/quantities", response_model=BimQuantitiesResponse)
async def quantities(request: Request) -> BimQuantitiesResponse:
    """Levanta quantidades (volume, área, comprimento) de um modelo IFC enviado no corpo.

    O corpo do pedido é o conteúdo do ficheiro ``.ifc`` (STEP), com o tipo
    ``application/octet-stream`` ou ``text/plain``. Limite: 25 MB.

    Raises:
        HTTPException: 413 se o ficheiro exceder o limite; 422 se não for um IFC legível.
    """
    body = await _read_body(request)
    try:
        return await run_in_threadpool(bim_service.extract_quantities, body)
    except bim_service.InvalidIfcError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
