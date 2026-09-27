# Bob and Codex usage

IBM Bob contributed the original engine, sample app, dashboard, custom modes, impact verdicts, proof tests and migration catalog. Existing commits and screenshots under bob_sessions/ document that historical work. Missing sessions are not reconstructed or claimed.

On 2026-09-27 the user explicitly ended the Bob-only workflow and asked Codex to complete the implementation. Codex restored the clean baseline, repaired and tested isolated copies of all three scenarios, fixed engine integration defects, completed convention checking and Docker impact, and published the final reports.

The nine Bob modes and four skills remain functional configuration: impact analyst, prover, migration planner, four module workers, convention scanner and verifier. Worker edit scopes include only their source module and their own repair artifact. The MCP launcher selects the engine environment on Windows or POSIX.

Final reports use provenance.generatedBy=codex. S1/S2 retain the original Bob verdicts, including S2's three false negatives. Codex's post-evaluation tests and repairs do not improve the recorded prediction scores. The guide catalog remains traceable to the official Pydantic migration guide; Codex corrected its from_orm detection pattern.

The convention comparison consists of two real Codex-authored variants run against the same contract tests. It is not represented as a Bob run or parallel-agent experiment. Both preserve behavior; one has a local-import convention violation and the accepted variant reuses existing module-level imports.

The default readiness checker distinguishes technical completion from historical Bob evidence. Use --require-bob-evidence to enforce the original screenshot targets. Missing historical screenshots remain a limitation of competition evidence, not a claim that the software is unfinished.
