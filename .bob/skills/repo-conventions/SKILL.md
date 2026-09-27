---
name: repo-conventions
description: Learn the coding conventions a repository already follows (naming, imports, error handling, file layout) and record them with evidence. Use before repairing code so the fixes match the repo's own style.
---

# Repo conventions

Goal: describe how THIS repo is written, as evidence, not taste.

## Procedure
1. Pick 8 to 12 representative files across modules: a service, a route file, a schema file, the errors file, requirements.txt, and 2 to 3 tests.
2. For each dimension below, write what you observed and cite at least TWO files as evidence. If the repo is not consistent, write "mixed" and cite one example of each style.
   - naming: variables and functions, classes, files and folders
   - imports: absolute vs relative, `from x import y` vs `import x`, ordering
   - errorHandling: raise typed exceptions vs return None vs result objects; which exception classes exist and where they live
   - fileLayout: one concern per module? where tests live and how they are named
3. Output .uplift/conventions.json: {"naming": "...", "imports": "...", "errorHandling": "...", "fileLayout": "...", "evidenceFiles": ["path", "..."]}.

## Never
- Never edit source files. Never state a convention you cannot cite.
