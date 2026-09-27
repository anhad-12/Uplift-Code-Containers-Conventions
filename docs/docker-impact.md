# Docker impact

The engine parses logical Dockerfile instructions, COPY/ADD sources (including JSON form), named build stages, FROM dependencies and COPY --from dependencies. A matching changed file marks that instruction and later instructions in the same stage as potentially invalidated; dependent stages propagate the effect.

Indices are Dockerfile instruction positions, not actual image layer counts. BuildKit can prune stages, use cache mounts, or reuse cache in ways this static analysis cannot measure. No duration is estimated.

Conservative limits: variable sources are treated as potentially matching; .dockerignore exclusions are not used to suppress hits; a change to Dockerfile or .dockerignore invalidates all stages. Remote ADD sources are not matched against local changed paths. Wildcards use Python fnmatch and are an approximation of Docker's matching rules. Nested build contexts and per-Dockerfile ignore files are not inferred. These can produce false positives; use an actual Docker build for exact costs.

The sample Dockerfile copies requirements before shop source, so a source-only edit avoids the dependency-install instructions. The dashboard renders these effects as infrastructure nodes.

Reference: https://docs.docker.com/reference/dockerfile/
