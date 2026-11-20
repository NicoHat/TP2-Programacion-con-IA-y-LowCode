import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.ia import IAError

log = logging.getLogger("api")


def _mensaje_validacion(e: dict) -> str:
    ctx = e.get("ctx") or {}
    tipo = e.get("type", "")
    if tipo == "missing":
        return "es obligatorio"
    if tipo == "string_too_short":
        return f"debe tener al menos {ctx.get('min_length')} caracteres"
    if tipo == "string_too_long":
        return f"no puede superar los {ctx.get('max_length')} caracteres"
    if tipo == "string_pattern_mismatch":
        return "no tiene un formato válido"
    if tipo == "literal_error":
        opciones = str(ctx.get("expected", "")).replace("'", "").replace(" or ", " o ")
        return f"debe ser uno de: {opciones}"
    if tipo in ("int_parsing", "int_type"):
        return "debe ser un número entero"
    if tipo == "greater_than":
        return f"debe ser mayor que {ctx.get('gt')}"
    if tipo == "json_invalid":
        return "el cuerpo no es un JSON válido"
    if tipo == "value_error":
        return str(ctx.get("error", e.get("msg", "valor inválido")))
    return e.get("msg", "valor inválido")


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
            campo = ".".join(str(p) for p in e["loc"] if p not in ("body", "query", "path") and not isinstance(p, int))
            mensaje = _mensaje_validacion(e)
            errores.append(f"{campo}: {mensaje}" if campo and e.get("type") != "json_invalid" else mensaje)
        return JSONResponse(status_code=422,
                            content={"detail": "Datos inválidos. " + " | ".join(errores),
                                     "errores": errores})
