"""Named callbacks and ordered listener collections."""

from __future__ import annotations

from collections.abc import Callable
from typing import Generic, ParamSpec, Protocol, TypeAlias, TypeVar, runtime_checkable
from uuid import uuid4

P = ParamSpec("P")
R = TypeVar("R")
R_co = TypeVar("R_co", covariant=True)


@runtime_checkable
class Listener(Protocol[P, R_co]):
    """A callable identified uniquely within a :class:`Listeners` collection."""

    @property
    def identifier(self) -> str:
        """Return the stable identifier used for listener replacement."""
        ...

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R_co:
        """Invoke the listener callback."""
        ...

    @staticmethod
    def create(callback: Callable[P, R], name: str) -> Listener[P, R]:
        """Wrap ``callback`` in a listener identified by ``name``."""
        return SimpleListener(callback, name)


class SimpleListener(Generic[P, R]):
    """A listener implemented by a caller-supplied callable and name."""

    def __init__(self, callback: Callable[P, R], name: str) -> None:
        self._callback = callback
        self._identifier = name

    @property
    def identifier(self) -> str:
        """Return the name supplied at construction."""
        return self._identifier

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        """Forward arguments and return the wrapped callback's result."""
        return self._callback(*args, **kwargs)

    @staticmethod
    def create(callback: Callable[P, R], name: str) -> Listener[P, R]:
        """Wrap ``callback`` in another simple listener."""
        return SimpleListener(callback, name)


ListenerOrCallable: TypeAlias = Listener[P, R] | Callable[P, R]


class Listeners(Generic[P, R]):
    """Ordered listeners with efficient lookup and cached ordered access.

    Adding an existing identifier replaces that listener in its current position.
    Plain callables are assigned a generated UUID identifier. Insertion and
    replacement may be linear; identifier lookup and :meth:`get_all` are O(1).
    """

    def __init__(self) -> None:
        self._by_identifier: dict[str, Listener[P, R]] = {}
        self._ordered: tuple[Listener[P, R], ...] = ()

    def add(self, listener: ListenerOrCallable[P, R]) -> Listener[P, R]:
        """Add or replace a listener and return its named representation."""
        resolved = listener if isinstance(listener, Listener) else Listener.create(listener, str(uuid4()))
        identifier = resolved.identifier
        if identifier in self._by_identifier:
            self._ordered = tuple(
                resolved if current.identifier == identifier else current for current in self._ordered
            )
        else:
            self._ordered += (resolved,)
        self._by_identifier[identifier] = resolved
        return resolved

    def get(self, identifier: str) -> Listener[P, R] | None:
        """Return the listener with ``identifier``, if present."""
        return self._by_identifier.get(identifier)

    def get_all(self) -> tuple[Listener[P, R], ...]:
        """Return the cached immutable listeners in execution order in O(1)."""
        return self._ordered

    def remove(self, identifier: str) -> Listener[P, R] | None:
        """Remove and return the listener with ``identifier``, if present."""
        listener = self._by_identifier.pop(identifier, None)
        if listener is not None:
            self._ordered = tuple(current for current in self._ordered if current.identifier != identifier)
        return listener

    def clear(self) -> None:
        """Remove every listener."""
        self._by_identifier.clear()
        self._ordered = ()

    def __len__(self) -> int:
        """Return the number of unique listener identifiers."""
        return len(self._by_identifier)


__all__ = ["Listener", "ListenerOrCallable", "Listeners", "SimpleListener"]
