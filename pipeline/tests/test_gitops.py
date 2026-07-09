import pytest

from pipeline import gitops


def test_commit_con_autor_de_drive(tmp_path):
    gitops.init_repo(tmp_path)
    (tmp_path / "a.md").write_text("hola", encoding="utf-8")
    sha = gitops.commit_paths(
        tmp_path,
        ["a.md"],
        "sync(ventas): a — alta",
        author_name="Nick R.",
        author_email="nick@example.com",
        author_date="2026-07-08T14:32:00Z",
    )
    assert sha
    out = gitops.git(["log", "-1", "--format=%an|%ae|%cn"], tmp_path).stdout.strip()
    assert out == f"Nick R.|nick@example.com|{gitops.COMMITTER_NAME}"

    # sin cambios → no hay commit
    assert gitops.commit_paths(tmp_path, ["a.md"], "nada") is None
    # pathspec inexistente → no explota
    assert gitops.commit_paths(tmp_path, ["no-existe.md"], "nada") is None


def test_commit_acotado_a_paths(tmp_path):
    gitops.init_repo(tmp_path)
    (tmp_path / "a.md").write_text("a", encoding="utf-8")
    (tmp_path / "b.md").write_text("b", encoding="utf-8")
    gitops.commit_paths(tmp_path, ["a.md"], "solo a")
    status = gitops.git(["status", "--porcelain"], tmp_path).stdout
    assert "b.md" in status  # b quedó fuera del commit


def test_guardrail_sin_remoto(tmp_path):
    gitops.init_repo(tmp_path)
    gitops.assert_no_remote(tmp_path)  # no levanta
    gitops.git(["remote", "add", "origin", "https://example.com/x.git"], tmp_path)
    with pytest.raises(gitops.GuardRailError):
        gitops.assert_no_remote(tmp_path)
