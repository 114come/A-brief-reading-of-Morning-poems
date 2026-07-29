from app.services.model.models import DataField, DataModel


def test_models_importable() -> None:
    assert DataModel.__tablename__ == "data_models"
    assert DataField.__tablename__ == "data_fields"
