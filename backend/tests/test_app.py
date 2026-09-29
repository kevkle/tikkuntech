def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_unknown_route_is_404(client):
    assert client.get("/nope").status_code == 404
