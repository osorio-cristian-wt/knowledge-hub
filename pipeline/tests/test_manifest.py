from pipeline.manifest import Manifest


def test_roundtrip_y_curados(tmp_path):
    path = tmp_path / "_meta" / "manifest.json"
    m = Manifest.load(path)
    assert m.page_token is None

    entry = m.add_curated("abc123def456", "folder", "/cleanora/ventas/", "chat", "Ventas")
    assert entry["dest"] == "cleanora/ventas"  # normalizado
    # alta repetida no duplica
    assert m.add_curated("abc123def456", "folder", "x", "chat", "Ventas") is entry
    assert len(m.curated) == 1

    m.page_token = "999"
    m.files["abc123def456"] = {"drive_id": "abc123def456", "pending_commit": {"action": "nuevo", "paths": []}}
    m.save()

    m2 = Manifest.load(path)
    assert m2.page_token == "999"
    assert m2.curated_by_id()["abc123def456"]["name"] == "Ventas"
    assert len(m2.pending_commits()) == 1

    assert m2.remove_curated("abc123def456")["drive_id"] == "abc123def456"
    assert m2.remove_curated("no-existe") is None
    assert m2.curated == []
