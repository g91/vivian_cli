"""Secure storage compatibility surface."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class _FileSecureStorage:
	def __init__(self, path: Path) -> None:
		self._path = path

	def read(self) -> dict[str, Any]:
		try:
			if not self._path.exists():
				return {}
			return json.loads(self._path.read_text(encoding="utf-8"))
		except Exception:
			return {}

	def update(self, value: dict[str, Any]) -> dict[str, Any]:
		try:
			self._path.parent.mkdir(parents=True, exist_ok=True)
			self._path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
			return {"success": True}
		except Exception as exc:
			return {"success": False, "error": str(exc)}


_SECURE_STORAGE = _FileSecureStorage(Path.home() / ".vivian" / "secure_storage.json")


def getSecureStorage() -> _FileSecureStorage:
	return _SECURE_STORAGE


def get_secure_storage() -> _FileSecureStorage:
	return getSecureStorage()


__all__ = ["getSecureStorage", "get_secure_storage"]
