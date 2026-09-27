# Convention-aware repair comparison

Both variants are actual Codex-authored repairs of create_order on the same
isolated S1 patch. Both run the orders suite and unchanged unknown-user proof.
See generic.json and convention-aware.json for measured counts and commands.
These are not IBM Bob task runs, and neither patch is claimed to have been
produced by a separate agent or a parallel worker.

The generic repair imports an aliased domain exception inside the function.
It preserves behavior, but violates the observed module-level import convention.
The convention-aware repair reuses the existing NotFoundError import and the
existing translation to ValidationError. It adds no import or exception alias.
Both preserve the 422 unknown-user contract. Added lines are checked for naming,
absolute/module-level imports, and typed raises. Generic has one violation;
convention-aware has none. No retry was required for the accepted variant.

Reproduce: engine/.venv/Scripts/python scripts/convention_demo.py (Windows).
Use engine/.venv/bin/python on POSIX.
