# core/di.py — Lightweight Dependency Injection Container for JARVIS MK37
from __future__ import annotations

import inspect
import logging
import threading
from typing import Any, Callable, Dict, List, Set, Type, TypeVar

T = TypeVar("T")

_logger = logging.getLogger("JARVIS.DI")


class Container:
    """Thread-safe Dependency Injection Container with proper transient/singleton semantics."""

    def __init__(self):
        # Registered concrete instances (always returned as-is)
        self._instances: Dict[Type[Any], Any] = {}
        # Lazy singleton factories — instantiated once and cached
        self._singleton_factories: Dict[Type[Any], Callable[[], Any]] = {}
        # Transient factories — create a new instance on every resolve()
        self._transient_factories: Dict[Type[Any], Callable[[], Any]] = {}
        # Cache for resolved singleton factories
        self._singleton_cache: Dict[Type[Any], Any] = {}
        self._lock = threading.RLock()

    # ── Registration ──────────────────────────────────────────────────────────

    def register_instance(self, interface: Type[T], instance: T) -> None:
        """Register an existing concrete instance (always returned as-is)."""
        with self._lock:
            self._instances[interface] = instance

    def register_singleton(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Register a lazy singleton factory — instantiated once, then cached."""
        with self._lock:
            self._singleton_factories[interface] = factory
            # Clear any previously cached singleton so the new factory is used
            self._singleton_cache.pop(interface, None)
            # Remove from transient if it was previously registered there
            self._transient_factories.pop(interface, None)

    def register_transient(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Register a transient factory — creates a NEW instance on every resolve()."""
        with self._lock:
            self._transient_factories[interface] = factory
            # Transients must NOT be in singleton registries
            self._singleton_factories.pop(interface, None)
            self._singleton_cache.pop(interface, None)

    # ── Resolution ────────────────────────────────────────────────────────────

    def resolve(self, interface: Type[T]) -> T:
        """Resolve an instance for the requested interface or class type."""
        with self._lock:
            # 1. Direct registered instance
            if interface in self._instances:
                return self._instances[interface]

            # 2. Transient — always create a fresh instance (NOT cached)
            if interface in self._transient_factories:
                return self._transient_factories[interface]()

            # 3. Singleton — check cache first, then create and cache
            if interface in self._singleton_factories:
                if interface not in self._singleton_cache:
                    self._singleton_cache[interface] = self._singleton_factories[interface]()
                return self._singleton_cache[interface]

            # 4. Auto-instantiation attempt for concrete classes with parameterless __init__
            if inspect.isclass(interface):
                try:
                    instance = interface()
                    self._instances[interface] = instance
                    return instance
                except Exception as exc:
                    raise KeyError(f"Could not auto-resolve class {interface.__name__}: {exc}") from exc

            raise KeyError(f"No registration found for interface {interface}")

    # ── Introspection ─────────────────────────────────────────────────────────

    def is_registered(self, interface: Type[Any]) -> bool:
        """Check whether a type has any registration (instance, singleton, or transient)."""
        with self._lock:
            return (
                interface in self._instances
                or interface in self._singleton_factories
                or interface in self._transient_factories
            )

    def registered_types(self) -> List[str]:
        """Return human-readable list of all registered type names (for debugging)."""
        with self._lock:
            all_types: Set[Type[Any]] = (
                set(self._instances) | set(self._singleton_factories) | set(self._transient_factories)
            )
            return sorted(t.__name__ for t in all_types if hasattr(t, "__name__"))

    def clear(self) -> None:
        """Clear all container registrations (useful for tests)."""
        with self._lock:
            self._instances.clear()
            self._singleton_factories.clear()
            self._transient_factories.clear()
            self._singleton_cache.clear()

    def __repr__(self) -> str:
        with self._lock:
            n_inst = len(self._instances)
            n_sing = len(self._singleton_factories)
            n_tran = len(self._transient_factories)
        return f"<Container instances={n_inst} singletons={n_sing} transients={n_tran}>"


# ── Global singleton container ────────────────────────────────────────────────
_global_container = Container()


def get_container() -> Container:
    """Return the global DI container instance."""
    return _global_container
