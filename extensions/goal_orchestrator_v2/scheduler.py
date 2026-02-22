from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime
from typing import Awaitable, Callable

from .config import settings


class AutoScheduler:
    def __init__(self, tick_fn: Callable[[], Awaitable[None]]):
        self.tick_fn = tick_fn
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    def _is_night(self) -> bool:
        hour = datetime.now().hour
        start = settings.night_start_hour
        end = settings.night_end_hour
        if start <= end:
            return start <= hour < end
        return hour >= start or hour < end

    def _interval(self) -> int:
        return settings.night_poll_seconds if self._is_night() else settings.day_poll_seconds

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                await self.tick_fn()
            except Exception:
                # scheduler must not crash the app loop
                pass
            if self._stop.is_set():
                break
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self._interval())
            except asyncio.TimeoutError:
                continue

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
