"""All sources of one board, refreshed on a timer."""

from __future__ import annotations

import threading
from pathlib import Path

from speccify_core.board import BoardSpec

from speccify_board.config import BoardConfig
from speccify_board.sources import Source


class Registry:
    def __init__(self, config: BoardConfig, data_dir: Path) -> None:
        self.config = config
        self.data_dir = data_dir
        self.sources: dict[str, Source] = {
            repo.name: Source(
                config=repo,
                data_dir=data_dir,
                author_name=config.author_name,
                author_email=config.author_email,
            )
            for repo in config.repos
        }
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def refresh_all(self) -> None:
        for source in self.sources.values():
            source.refresh()

    def specs(self, name: str | None = None) -> list[BoardSpec]:
        if name is not None:
            return list(self.sources[name].state.specs)
        return [spec for source in self.sources.values() for spec in source.state.specs]

    def status(self) -> list[dict[str, object]]:
        return [
            {
                "name": source.name,
                "kind": "git" if source.config.is_remote else "path",
                "branch": source.config.branch if source.config.is_remote else None,
                "commit": source.state.commit,
                "refreshed_at": source.state.refreshed_at,
                "error": source.state.error,
                "specs": len(source.state.specs),
            }
            for source in self.sources.values()
        ]

    def source_label(self) -> str:
        parts = []
        for source in self.sources.values():
            if source.state.error:
                parts.append(f"{source.name}: Fehler")
            elif source.state.commit:
                parts.append(f"{source.name}@{source.state.commit}")
            else:
                parts.append(source.name)
        return " · ".join(parts) or "keine Repos"

    def start(self) -> None:
        if self._thread is not None:
            return

        def loop() -> None:
            while not self._stop.wait(self.config.refresh_seconds):
                self.refresh_all()

        self.refresh_all()
        self._thread = threading.Thread(target=loop, name="board-refresh", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
