from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from shop.errors import NotFoundError, ValidationError
from shop.orders.routes import router as orders_router
from shop.payments.routes import router as payments_router
from shop.users.routes import router as users_router


def create_app() -> FastAPI:
    app = FastAPI(title="Shop")

    @app.exception_handler(NotFoundError)
    async def not_found(request: Request, exc: NotFoundError):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(ValidationError)
    async def invalid(request: Request, exc: ValidationError):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    for router in (users_router, orders_router, payments_router):
        app.include_router(router)
    return app


app = create_app()
