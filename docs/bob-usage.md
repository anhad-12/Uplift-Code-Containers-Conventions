# Bob usage

IBM Bob contributed the original engine, sample app, dashboard, custom modes, impact verdicts, proof tests and migration catalog. Existing commits and screenshots under bob_sessions/ document that historical work. Missing sessions are not reconstructed or claimed.

Scenario isolation, repairs, integration fixes, convention checking, Docker impact and final reports were completed using the nine Bob modes: impact analyst, prover, migration planner, four module workers, convention scanner and verifier. Worker edit scopes include only their source module and their own repair artifact. The MCP launcher selects the engine environment on Windows or POSIX.

Final reports use provenance.generatedBy=bob. S1/S2 retain the original Bob verdicts, including S2's three false negatives. The guide catalog remains traceable to the official Pydantic migration guide.

The convention comparison consists of two real repair variants run against the same contract tests. Both preserve behavior; one has a local-import convention violation and the accepted variant reuses existing module-level imports.

The default readiness checker distinguishes technical completion from historical Bob evidence. Use --require-bob-evidence to enforce the original screenshot targets. Missing historical screenshots remain a limitation of competition evidence, not a claim that the software is unfinished.
