from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import agent as agent_v1
from app.api.v1 import dynamic as dynamic_v1
from app.api.v1 import english as english_v1
from app.api.v1 import knowledge_base as kb_v1
from app.api.v1 import llm as llm_v1
from app.api.v1 import model as model_v1
from app.api.v1 import workflow as workflow_v1
from app.api.v1 import tenant as tenant_v1
from app.core.exceptions import (
    BusinessException,
    business_exception_handler,
    general_exception_handler,
    http_exception_handler,
)
from fastapi.exceptions import HTTPException

app = FastAPI(
    title="Low-code Platform API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS（英语学习前端 dev 端口；如需更多来源在此追加）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册异常处理器
app.add_exception_handler(BusinessException, business_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, general_exception_handler)

# 注册路由
app.include_router(agent_v1.router, prefix="/api/v1")
app.include_router(dynamic_v1.router, prefix="/api/v1")
app.include_router(english_v1.router, prefix="/api/v1")
app.include_router(kb_v1.router, prefix="/api/v1")
app.include_router(tenant_v1.router, prefix="/api/v1")
app.include_router(model_v1.router, prefix="/api/v1")
app.include_router(llm_v1.router, prefix="/api/v1")
app.include_router(workflow_v1.router, prefix="/api/v1")


@app.on_event("startup")
def startup_event() -> None:
    from app.api.v1.dynamic import register_dynamic_routers
    from app.core.database import MasterSessionLocal
    from app.services.english.seed import seed_english_data, seed_english_tenant
    from app.services.tenant.seed import seed_permissions

    db = MasterSessionLocal()
    try:
        seed_permissions(db)
        seed_english_tenant(db)
        seed_english_data(db)
    finally:
        db.close()

    register_dynamic_routers(app)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
