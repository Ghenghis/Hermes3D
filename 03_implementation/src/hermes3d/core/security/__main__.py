"""Allow ``python -m hermes3d.core.security`` to invoke the scanner CLI.

The brief specifies the longer form
``python -m hermes3d.core.security.injection_scanner`` as the entry point;
that path is supported via Python's import machinery automatically because
``injection_scanner`` is already an importable module — running it as
``-m hermes3d.core.security.injection_scanner`` triggers any ``__main__``
guard inside that file. To avoid a confusing ``runpy`` re-import warning
caused by the package's ``__init__`` re-exporting symbols from
``injection_scanner``, we prefer this ``__main__.py`` shim and keep the
documented CLI implementation in :mod:`hermes3d.core.security.cli`.

Both invocations produce identical behaviour::

    python -m hermes3d.core.security <args>
    python -m hermes3d.core.security.cli <args>
"""

from hermes3d.core.security.cli import main

if __name__ == "__main__":  # pragma: no cover - CLI bootstrap
    raise SystemExit(main())
