from app.core.response import UnifiedResponse


class TestUnifiedResponse:
    def test_default_values(self) -> None:
        resp = UnifiedResponse()
        assert resp.code == 0
        assert resp.data is None
        assert resp.message == "ok"

    def test_success_with_data(self) -> None:
        resp = UnifiedResponse.success(data={"id": 1})
        assert resp.code == 0
        assert resp.data == {"id": 1}
        assert resp.message == "ok"

    def test_success_with_custom_message(self) -> None:
        resp = UnifiedResponse.success(data=[1, 2, 3], message="list retrieved")
        assert resp.code == 0
        assert resp.data == [1, 2, 3]
        assert resp.message == "list retrieved"

    def test_success_with_none_data(self) -> None:
        resp = UnifiedResponse.success()
        assert resp.code == 0
        assert resp.data is None
        assert resp.message == "ok"

    def test_error(self) -> None:
        resp = UnifiedResponse.error(code=400001, message="bad request")
        assert resp.code == 400001
        assert resp.data is None
        assert resp.message == "bad request"

    def test_model_dump(self) -> None:
        resp = UnifiedResponse.success(data="hello")
        dumped = resp.model_dump()
        assert dumped == {"code": 0, "data": "hello", "message": "ok"}
