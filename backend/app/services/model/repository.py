from typing import Any

from sqlalchemy.orm import Session

from app.services.model.models import DataField, DataModel


class DataModelRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **kwargs: Any) -> DataModel:
        model = DataModel(**kwargs)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    def get_by_id(self, model_id: int) -> DataModel | None:
        return self.db.query(DataModel).filter(DataModel.id == model_id).first()

    def get_by_table_name(self, table_name: str, tenant_id: int) -> DataModel | None:
        return (
            self.db.query(DataModel)
            .filter(DataModel.table_name == table_name, DataModel.tenant_id == tenant_id)
            .first()
        )

    def list_by_tenant(self, tenant_id: int, skip: int = 0, limit: int = 100) -> list[DataModel]:
        return (
            self.db.query(DataModel)
            .filter(DataModel.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update(self, model_id: int, **kwargs: Any) -> DataModel | None:
        model = self.get_by_id(model_id)
        if not model:
            return None
        for key, value in kwargs.items():
            if hasattr(model, key):
                setattr(model, key, value)
        self.db.commit()
        self.db.refresh(model)
        return model

    def delete(self, model_id: int) -> bool:
        model = self.get_by_id(model_id)
        if not model:
            return False
        self.db.delete(model)
        self.db.commit()
        return True


class DataFieldRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **kwargs: Any) -> DataField:
        field = DataField(**kwargs)
        self.db.add(field)
        self.db.commit()
        self.db.refresh(field)
        return field

    def list_by_model(self, model_id: int) -> list[DataField]:
        return (
            self.db.query(DataField)
            .filter(DataField.model_id == model_id)
            .order_by(DataField.sort_order)
            .all()
        )
