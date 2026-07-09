"""Operaciones git sobre el repo conocimiento (§3.4, DD-16; guard-rail C-02).

Autor de cada commit = quien modificó en Drive; committer fijo "Claw Sync".
Así `git log` responde "quién cambió qué y cuándo" sin exponerle git a Daiana.
"""

import os
import subprocess
from pathlib import Path

COMMITTER_NAME = "Claw Sync"
COMMITTER_EMAIL = "claw-sync@localhost"


class GuardRailError(Exception):
    """El repo conocimiento tiene remoto: prohibido por diseño (C-02, DD-15)."""


def git(args: list[str], cwd, env_extra: dict | None = None, check: bool = True):
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} falló: {result.stderr.strip()}")
    return result


def init_repo(root: Path) -> None:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    if not (root / ".git").exists():
        git(["init", "-b", "main"], root)
        git(["config", "user.name", COMMITTER_NAME], root)
        git(["config", "user.email", COMMITTER_EMAIL], root)


def assert_no_remote(root: Path) -> None:
    """Se verifica antes de cada corrida: si alguien agregó remoto, frenar y avisar."""
    out = git(["remote"], root).stdout.strip()
    if out:
        raise GuardRailError(
            f"El repo de conocimiento tiene remotos configurados ({out.replace(chr(10), ', ')}). "
            "Prohibido por diseño (C-02): los datos de la empresa no salen de esta PC. "
            "Eliminar el remoto antes de volver a sincronizar."
        )


def _existing_pathspecs(root: Path, paths) -> list[str]:
    """Filtra pathspecs que no existen ni están trackeados (git add fallaría)."""
    keep = []
    for p in paths:
        rel = str(p).replace("\\", "/")
        if (root / rel).exists():
            keep.append(rel)
            continue
        if git(["ls-files", "--", rel], root, check=False).stdout.strip():
            keep.append(rel)
    return keep


def commit_paths(
    root: Path,
    paths,
    message: str,
    author_name: str | None = None,
    author_email: str | None = None,
    author_date: str | None = None,
) -> str | None:
    """Un commit acotado a `paths`. Devuelve el hash, o None si no había cambios."""
    root = Path(root)
    rel = _existing_pathspecs(root, paths)
    if not rel:
        return None
    git(["add", "-A", "--", *rel], root)
    if git(["diff", "--cached", "--quiet", "--", *rel], root, check=False).returncode == 0:
        return None
    env = {
        "GIT_AUTHOR_NAME": author_name or COMMITTER_NAME,
        "GIT_AUTHOR_EMAIL": author_email or COMMITTER_EMAIL,
        "GIT_COMMITTER_NAME": COMMITTER_NAME,
        "GIT_COMMITTER_EMAIL": COMMITTER_EMAIL,
    }
    if author_date:
        env["GIT_AUTHOR_DATE"] = author_date
    git(["commit", "-m", message, "--", *rel], root, env_extra=env)
    return git(["rev-parse", "HEAD"], root).stdout.strip()


def commit_all(root: Path, message: str) -> str | None:
    """Commit de todo el working tree (solo para el esqueleto inicial)."""
    root = Path(root)
    git(["add", "-A"], root)
    if git(["diff", "--cached", "--quiet"], root, check=False).returncode == 0:
        return None
    env = {
        "GIT_AUTHOR_NAME": COMMITTER_NAME,
        "GIT_AUTHOR_EMAIL": COMMITTER_EMAIL,
        "GIT_COMMITTER_NAME": COMMITTER_NAME,
        "GIT_COMMITTER_EMAIL": COMMITTER_EMAIL,
    }
    git(["commit", "-m", message], root, env_extra=env)
    return git(["rev-parse", "HEAD"], root).stdout.strip()
