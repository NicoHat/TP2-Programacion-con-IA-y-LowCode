import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.ia import IAError

log = logging.getLogger("api")


def _status_para_value_error(mensaje: str) -> int:
    m = mensaje.lower()
    if "ya existe" in m or "ya pertenece" in m:
        return 409
    if "no existe" in m:
        return 404
    return 400


def registrar_manejadores(app: FastAPI) -> None:

    @app.exception_handler(ValueError)
    async def value_error(_: Request, exc: ValueError):
        return JSONResponse(status_code=_status_para_value_error(str(exc)),
                            content={"detail": str(exc)})

    @app.exception_handler(RuntimeError)
    async def runtime_error(_: Request, exc: RuntimeError):
        log.exception("Error interno: %s", exc)
        return JSONResponse(status_code=500,
                            content={"detail": "Error interno del servidor de datos. Revisar logs de la API."})

    @app.exception_handler(IAError)
    async def ia_error(_: Request, exc: IAError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.mensaje})

    @app.exception_handler(RequestValidationError)
    async def validacion(_: Request, exc: RequestValidationError):
        errores = []
        for e in exc.errors():
            campo = ".".join(str(p) for p in e["loc"] if p not in ("body", "query", "path"))
            errores.append(f"{campo or 'request'}: {e['msg']}")
        return JSONResponse(status_code=422,
                            content={"detail": "Datos inválidos. " + " | ".join(errores),
                                     "errores": errores})
