"""Import warning persistence and admin history regression test."""


def test_import_warnings_survive_in_admin_history(client, make_user):
    key = {"X-Import-Key": "test-import-key"}
    source = {"code": "warning_history_test"}

    def record(external_id):
        return {
            "external_id": external_id,
            "name": "Warning History Clinic",
            "facility_type": "clinic",
            "town": "Embu",
            "county": "Embu",
        }

    def submit(external_id):
        response = client.post(
            "/api/import/facilities",
            headers=key,
            json={
                "source": source,
                "is_demo": True,
                "facilities": [record(external_id)],
            },
        )
        assert response.status_code == 200, response.text
        return response.json()

    first = submit("warning-first")
    assert first["created"] == 1

    second = submit("warning-second")
    assert second["created"] == 1
    assert second["warnings"], "Expected duplicate-name warning"

    admin_headers = make_user(role="admin")[1]
    response = client.get("/api/admin/imports", headers=admin_headers)
    assert response.status_code == 200, response.text

    matching = [
        batch for batch in response.json()
        if batch["id"] == second["batch_id"]
    ]
    assert len(matching) == 1
    assert matching[0]["warnings"] == second["warnings"]
