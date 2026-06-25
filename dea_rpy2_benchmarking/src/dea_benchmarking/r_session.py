"""rpy2 <-> R bridge for the Benchmarking package.

This module owns *all* the fragile setup of the R runtime. Import anything you
need from here; never call ``import rpy2`` directly elsewhere in the package,
because a few environment variables MUST be set before rpy2 is first imported.

Why the dance:
- rpy2 is installed from a prebuilt wheel that may have been compiled against a
  different R than the one on this machine (e.g. a CRAN framework R vs. the
  Homebrew R 4.6 we actually use). Forcing ABI mode and pinning ``R_HOME`` to
  the active R makes the binding load the correct ``libR``.
- ``R_HOME`` is detected dynamically via ``R RHOME`` so this keeps working if R
  is upgraded or installed somewhere else.

Public surface:
- ``get_benchmarking()`` -> the full ``Benchmarking`` R package object. Every
  function in the package is reachable as an attribute (R's ``.`` becomes ``_``
  in rpy2, e.g. ``dea.boot`` -> ``dea_boot``). This is the "everything is
  available" escape hatch.
- ``r`` -> the rpy2 ``robjects.r`` evaluator, for raw R code when needed.
- ``importr`` -> re-export, to load any other R package (``stats``, ``utils``…).
"""

from __future__ import annotations

import os
import subprocess
from functools import lru_cache


def _detect_r_home() -> str | None:
    """Return the active R's home dir via ``R RHOME``, or None if R is absent."""
    if os.environ.get("R_HOME"):
        return os.environ["R_HOME"]
    for exe in ("R", "/opt/homebrew/bin/R", "/usr/local/bin/R"):
        try:
            out = subprocess.run(
                [exe, "RHOME"], capture_output=True, text=True, check=True
            )
            return out.stdout.strip()
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    return None


def _configure_environment() -> None:
    """Set env vars that rpy2 reads at import time. Idempotent."""
    # Prefer the stable ABI binding over the prebuilt API one, which may be
    # linked against a different R and fail to dlopen libRblas/libR.
    os.environ.setdefault("RPY2_CFFI_MODE", "ABI")
    r_home = _detect_r_home()
    if r_home:
        os.environ.setdefault("R_HOME", r_home)


# Must run before rpy2 is imported anywhere in the process.
_configure_environment()

import rpy2.robjects as ro  # noqa: E402
from rpy2.robjects import default_converter, numpy2ri  # noqa: E402
from rpy2.robjects.packages import importr  # noqa: E402

# Re-exports for convenience.
r = ro.r

# rpy2 >= 3.5 deprecated the global ``numpy2ri.activate()``. The current idiom
# is a scoped converter context. ``np_converter`` merges the default rules with
# numpy <-> R array conversion; use it as ``with np_converter.context(): ...``
# around any code that passes numpy arrays into R or reads R arrays back out.
np_converter = default_converter + numpy2ri.converter


@lru_cache(maxsize=1)
def get_benchmarking():
    """Load and return the ``Benchmarking`` R package object (cached).

    Raises a clear error if the package is not installed in the active R.
    """
    try:
        return importr("Benchmarking")
    except Exception as exc:  # rpy2 raises a package-not-found error
        raise RuntimeError(
            "The R package 'Benchmarking' is not installed in the active R "
            f"(R_HOME={os.environ.get('R_HOME')}).\n"
            "Install it with:\n"
            "    Rscript -e 'install.packages(\"Benchmarking\", "
            "repos=\"https://cloud.r-project.org\")'"
        ) from exc


def r_version() -> str:
    """Return the active R's version string (sanity check)."""
    return str(r("R.version.string")[0])


__all__ = [
    "r",
    "importr",
    "np_converter",
    "get_benchmarking",
    "r_version",
]
