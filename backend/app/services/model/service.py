import json

from sqlalchemy.orm import Session

from app.core.database import create_tenant_database, get_tenant_engine
from app.core.exceptions import ValidationException
from app.services.model.generator import generate_sqlalchemy_model
from app.services.model.mapper import map_json_schema_to_mysql
from app.services.model.models import DataField, DataModel
from app.services.model.repository import DataFieldRepository, DataModelRepository
from app.services.model.schemas import DataModelCreate
from app.services.tenant.models import Tenant


class ModelService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.model_repo = DataModelRepository(db)
        self.field_repo = DataFieldRepository(db)

    def create_model(self, tenant_id: int, data: DataModelCreate) -> DataModel:
        existing = self.model_repo.get_by_table_name(data.table_name, tenant_id)
        if existing:
            raise ValidationException(f"表名 {data.table_name} 已存在")

        properties: dict[str, dict[str, object]] = {}
        for field in data.fields:
            properties[field.name] = {
                "type": field.field_type,
                "title": field.label,
            }
            if field.constraints:
                properties[field.name].update(field.constraints)

        json_schema = json.dumps({
            "type": "object",
            "title": data.name,
            "properties": properties,
        })

        model = self.model_repo.create(
            tenant_id=tenant_id,
            name=data.name,
            table_name=data.table_name,
            description=data.description,
            json_schema=json_schema,
            status="draft",
        )

        for idx, field in enumerate(data.fields):
            db_type = map_json_schema_to_mysql(
                field.field_type,
                field.constraints or {},
            )
            self.field_repo.create(
                model_id=model.id,
                name=field.name,
                label=field.label,
                field_type=field.field_type,
                constraints=json.dumps(field.constraints) if field.constraints else None,
                db_column_type=db_type,
                sort_order=idx,
            )

        self.db.refresh(model)
        return model

    def get_model_with_fields(self, model_id: int) -> DataModel | None:
        return self.model_repo.get_by_id(model_id)

    def update_model(self, model_id: int, data: DataModelCreate) -> DataModel:
        model = self.model_repo.get_by_id(model_id)
        if not model:
            raise ValidationException("模型不存在")

        # Check table_name uniqueness if it changed
        if data.table_name != model.table_name:
            existing = self.model_repo.get_by_table_name(data.table_name, model.tenant_id)
            if existing:
                raise ValidationException(f"表名 {data.table_name} 已存在")

        # Rebuild json_schema
        properties: dict[str, dict[str, object]] = {}
        for field in data.fields:
            properties[field.name] = {
                "type": field.field_type,
                "title": field.label,
            }
            if field.constraints:
                properties[field.name].update(field.constraints)

        json_schema = json.dumps({
            "type": "object",
            "title": data.name,
            "properties": properties,
        })

        # Update model
        model = self.model_repo.update(
            model_id,
            name=data.name,
            table_name=data.table_name,
            description=data.description,
            json_schema=json_schema,
        )
        if not model:
            raise ValidationException("模型不存在")

        # Replace fields: delete old, insert new
        old_fields = self.field_repo.list_by_model(model_id)
        for f in old_fields:
            self.db.delete(f)
        self.db.flush()

        for idx, field in enumerate(data.fields):
            db_type = map_json_schema_to_mysql(field.field_type, field.constraints or {})
            self.field_repo.create(
                model_id=model.id,
                name=field.name,
                label=field.label,
                field_type=field.field_type,
                constraints=json.dumps(field.constraints) if field.constraints else None,
                db_column_type=db_type,
                sort_order=idx,
            )

        self.db.refresh(model)
        return model

    def delete_model(self, model_id: int) -> None:
        model = self.model_repo.get_by_id(model_id)
        if not model:
            raise ValidationException("模型不存在")
        self.model_repo.delete(model_id)

    def publish_model(self, model_id: int, tenant: Tenant) -> DataModel:
        model = self.model_repo.get_by_id(model_id)
        if not model:
            raise ValidationException("模型不存在")
        if model.status == "published":
            raise ValidationException("模型已发布")

        create_tenant_database(tenant)
        engine = get_tenant_engine(tenant)

        DynamicModel = generate_sqlalchemy_model(model)
        DynamicModel.__table__.create(engine, checkfirst=True)  # type: ignore[attr-defined]

        model.status = "published"
        self.db.commit()
        self.db.refresh(model)
        return model
