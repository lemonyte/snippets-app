from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from deta import Base

from models import Snippet

if TYPE_CHECKING:
    from uuid import UUID


class SnippetNotFoundError(Exception):
    pass


class SnippetExistsError(Exception):
    pass


class SnippetDB(ABC):
    @abstractmethod
    def get(self, id: UUID) -> Snippet:
        pass

    @abstractmethod
    def put(self, snippet: Snippet) -> UUID:
        pass

    @abstractmethod
    def delete(self, id: UUID) -> None:
        pass


class FileDB(SnippetDB):
    def __init__(self, path: Path = Path("./data/snippets")) -> None:
        self.path = path
        if not self.path.exists():
            self.path.mkdir(parents=True, exist_ok=True)

    def get(self, id: UUID) -> Snippet:
        try:
            path = self.path / f"{id}.json"
            return Snippet.model_validate_json(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise SnippetNotFoundError from exc

    def put(self, snippet: Snippet) -> UUID:
        path = self.path / f"{snippet.id}.json"
        if path.exists():
            raise SnippetExistsError
        path.write_text(snippet.model_dump_json(), encoding="utf-8")
        return snippet.id

    def delete(self, id: UUID) -> None:
        path = self.path / f"{id}.json"
        if path.exists():
            path.unlink()


class DetaDB(SnippetDB):
    def __init__(self, name: str) -> None:
        self._db = Base(name)

    def get(self, id: UUID) -> Snippet:
        try:
            snippet = next(iter(self._db.fetch({"id": str(id)}, limit=1).items))
        except StopIteration as exc:
            raise SnippetNotFoundError from exc
        return Snippet.model_validate(snippet)

    def put(self, snippet: Snippet) -> UUID:
        try:
            self._db.insert(snippet.model_dump(mode="json"), key=f"{snippet.creation_time}-{snippet.id}")
        except Exception as exc:
            raise SnippetExistsError from exc
        return snippet.id

    def delete(self, id: UUID) -> None:
        snippet = self.get(id)
        self._db.delete(f"{snippet.creation_time}-{snippet.id}")

    def fetch(self) -> list[Snippet]:
        return [Snippet.model_validate(snippet) for snippet in self._db.fetch(desc=True).items]
