import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from shop.errors import NotFoundError, ValidationError
from shop.orders import repo as order_repo
from shop.payments import repo as payment_repo


@pytest.fixture(autouse=True)
def clean_orders():
    order_repo.reset()
    payment_repo.reset()
    yield
    order_repo.reset()
    payment_repo.reset()


def make_client(router) -> TestClient:
    """A client for ONE router, so an import error in another module cannot break these tests."""
    app = FastAPI()

    @app.exception_handler(NotFoundError)
    async def not_found(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(ValidationError)
    async def invalid(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    app.include_router(router)
    return TestClient(app)
