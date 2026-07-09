from pipeline.curate import extract_drive_id


def test_urls_tipicas():
    assert (
        extract_drive_id("https://docs.google.com/document/d/1AbC-def_456xyz789/edit")
        == "1AbC-def_456xyz789"
    )
    assert (
        extract_drive_id("https://docs.google.com/spreadsheets/d/1AbCdef456xyz789/edit#gid=0")
        == "1AbCdef456xyz789"
    )
    assert (
        extract_drive_id("https://drive.google.com/drive/folders/1AbCdef456xyz789?usp=sharing")
        == "1AbCdef456xyz789"
    )
    assert (
        extract_drive_id("https://drive.google.com/open?id=1AbCdef456xyz789")
        == "1AbCdef456xyz789"
    )
    assert extract_drive_id("https://drive.google.com/file/d/1AbCdef456xyz789/view") == "1AbCdef456xyz789"


def test_id_pelado_y_basura():
    assert extract_drive_id("1AbCdef456xyz789") == "1AbCdef456xyz789"
    assert extract_drive_id("hola que tal") is None
    assert extract_drive_id("corto") is None
