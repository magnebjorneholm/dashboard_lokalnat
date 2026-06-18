"""
data_loaders/_cache.py

A thin caching shim so the data layer does not hard-depend on Streamlit.

When running inside Streamlit, ``cached`` delegates to ``st.cache_data`` (same
behaviour as before: TTL, no spinner). When Streamlit is unavailable or no
script-run context exists (pipeline, tests, scripts), it falls back to a plain
process-wide memo so loads still happen only once.

Usage mirrors ``st.cache_data``::

    @cached(ttl=3600)
    def load_something(path=None):
        ...
"""
from __future__ import annotations

import functools
from typing import Callable


def cached(ttl: int = 3600, show_spinner: bool | str = False) -> Callable:
    """Return a decorator that caches a loader result once per process/session."""
    def decorator(func: Callable) -> Callable:
        try:
            import streamlit as st
            return st.cache_data(ttl=ttl, show_spinner=show_spinner)(func)
        except Exception:
            # No Streamlit available — memoise on the argument tuple.
            memo: dict = {}

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                key = (args, tuple(sorted(kwargs.items())))
                if key not in memo:
                    memo[key] = func(*args, **kwargs)
                return memo[key]

            wrapper.clear = memo.clear  # parity with st.cache_data(...).clear()
            return wrapper
    return decorator
