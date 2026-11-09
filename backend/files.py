"""Deleting the app's own stored copies of course files."""

from __future__ import annotations

from pathlib import Path


def delete_stored_copy(folder: Path, name: str) -> bool:
    """Delete folder/<name> if it exists. Return True if a file was deleted.

    Only the bare file name is used, and the result must stay inside `folder`,
    so a name like "../x.pdf" can never delete anything outside it.
    """
    folder = Path(folder).resolve()
    target = (folder / Path(name).name).resolve()
    if target.parent != folder or not target.is_file():
        return False
    target.unlink()
    return True
