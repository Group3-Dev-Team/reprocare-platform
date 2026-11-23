"""Who can reach what: sign-in is required and each role only reaches its own pages."""


def test_protected_routes_require_sign_in(client):
    for path in ["/api/auth/me", "/api/me/saved", "/api/me/notifications", "/api/admin/overview", "/api/admin/users"]:
        assert client.get(path).status_code == 401, path


def test_roles_are_enforced(client, make_user, make_facility):
    _, patient = make_user()
    _, staff = make_user(role="facility_staff", facility=make_facility())
    assert client.get("/api/admin/overview", headers=patient).status_code == 403
    assert client.get("/api/admin/users", headers=patient).status_code == 403
    assert client.get("/api/admin/overview", headers=staff).status_code == 403
    # saved clinics are for patients only
    assert client.get("/api/me/saved", headers=staff).status_code == 403


def test_admin_creates_staff_account_for_a_facility(client, make_user, make_facility):
    _, admin = make_user(role="admin")
    facility = make_facility()
    body = {"full_name": "Clinic Staff", "email": "new.staff@example.com", "password": "Staff1234", "role": "facility_staff"}
    # staff must belong to a facility
    assert client.post("/api/admin/users", headers=admin, json=body).status_code == 400
    r = client.post("/api/admin/users", headers=admin, json={**body, "facility_slug": facility.slug})
    assert r.status_code == 201 and r.json()["role"] == "facility_staff"
    assert client.post("/api/admin/users", headers=admin, json={**body, "facility_slug": facility.slug}).status_code == 409
    # patients sign up themselves, an admin can't create one
    assert client.post("/api/admin/users", headers=admin, json={**body, "email": "p@example.com", "role": "patient"}).status_code == 422


def test_admin_cannot_deactivate_themselves(client, make_user):
    admin_user, admin = make_user(role="admin")
    assert client.patch(f"/api/admin/users/{admin_user.id}", headers=admin, json={"is_active": False}).status_code == 400


def test_notifications_belong_to_the_signed_in_user(client, make_user):
    _, first = make_user()
    r = client.get("/api/me/notifications", headers=first)
    assert r.status_code == 200 and r.json() == {"items": [], "unread": 0}
    assert client.post("/api/me/notifications/read", headers=first).status_code == 204