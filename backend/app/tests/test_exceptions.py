import json

import pytest
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    BusinessException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
    business_exception_handler,
    general_exception_handler,
    http_exception_handler,
)


@pytest.fixture
def dummy_request() -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "query_string": b"",
    }
    return Request(scope=scope)


class TestBusinessException:
    def test_default_values(self) -> None:
        exc = BusinessException()
        assert exc.code == 400000
        assert exc.message == "业务错误"

    def test_custom_values(self) -> None:
        exc = BusinessException(code=400001, message="custom error")
        assert exc.code == 400001
        assert exc.message == "custom error"


class TestUnauthorizedException:
    def test_default_values(self) -> None:
        exc = UnauthorizedException()
        assert exc.code == 401000
        assert exc.message == "未授权"

    def test_custom_message(self) -> None:
        exc = UnauthorizedException(message="custom unauthorized")
        assert exc.code == 401000
        assert exc.message == "custom unauthorized"


class TestForbiddenException:
    def test_default_values(self) -> None:
        exc = ForbiddenException()
        assert exc.code == 403000
        assert exc.message == "禁止访问"


class TestNotFoundException:
    def test_default_values(self) -> None:
        exc = NotFoundException()
        assert exc.code == 404000
        assert exc.message == "资源不存在"


class TestValidationException:
    def test_default_values(self) -> None:
        exc = ValidationException()
        assert exc.code == 422000
        assert exc.message == "参数校验失败"


@pytest.mark.asyncio
class TestExceptionHandlers:
    async def test_business_exception_handler(self, dummy_request: Request) -> None:
        exc = BusinessException(code=400001, message="business error")
        response = await business_exception_handler(dummy_request, exc)
        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        assert json.loads(bytes(response.body).decode("utf-8")) == {
            "code": 400001,
            "data": None,
            "message": "business error",
        }

    async def test_http_exception_handler(self, dummy_request: Request) -> None:
        exc = HTTPException(status_code=404, detail="not found")
        response = await http_exception_handler(dummy_request, exc)
        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        assert json.loads(bytes(response.body).decode("utf-8")) == {
            "code": 404000,
            "data": None,
            "message": "not found",
        }

    async def test_general_exception_handler(self, dummy_request: Request) -> None:
        exc = Exception("something went wrong")
        response = await general_exception_handler(dummy_request, exc)
        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        assert json.loads(bytes(response.body).decode("utf-8")) == {
            "code": 500000,
            "data": None,
            "message": "服务器内部错误",
        }
