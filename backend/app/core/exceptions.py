import logging

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class BusinessException(Exception):
    """业务异常基类"""

    def __init__(self, code: int = 400000, message: str = "业务错误") -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class UnauthorizedException(BusinessException):
    def __init__(self, message: str = "未授权") -> None:
        super().__init__(code=401000, message=message)


class ForbiddenException(BusinessException):
    def __init__(self, message: str = "禁止访问") -> None:
        super().__init__(code=403000, message=message)


class NotFoundException(BusinessException):
    def __init__(self, message: str = "资源不存在") -> None:
        super().__init__(code=404000, message=message)


class ValidationException(BusinessException):
    def __init__(self, message: str = "参数校验失败") -> None:
        super().__init__(code=422000, message=message)


async def business_exception_handler(request: Request, exc: BusinessException) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"code": exc.code, "data": None, "message": exc.message},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "code": exc.status_code * 1000,
            "data": None,
            "message": exc.detail,
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.exception("Unhandled error")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"code": 500000, "data": None, "message": "服务器内部错误"},
    )
