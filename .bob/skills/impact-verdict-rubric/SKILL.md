---
name: impact-verdict-rubric
description: Judge whether a changed function, route or dependency breaks one of its dependents. Use when deciding will_break, might_break or safe for an affected place.
---

# Impact verdict rubric

You are given: the change (a patch or a dependency upgrade), one changed symbol with its changeType and hints, and one dependent (a "candidate": file, function, code snippet). Decide what happens to the dependent.

## Procedure
1. Read the change. Write one plain sentence: "Before, X. After, Y." (for example: "Before, get_user raised NotFoundError for an unknown id. After, it returns None.")
2. Open the dependent's FULL function in its file (not only the snippet). Find every line that uses the changed symbol's result or behaviour.
3. Ask: does this code rely on the OLD behaviour? Check each of these traps:
   - raise vs return None: code that no longer sees an exception, or dereferences None (AttributeError, TypeError).
   - try/except that used to catch the old exception and now silently continues.
   - units and scale (dollars vs cents), rounding, ordering, defaults, mutability.
   - truthiness: `if result:` treats 0, "" and None the same.
   - HTTP: an exception handler used to turn the exception into a status code; a response_model that now receives None or a different shape (validation error, 500) or a route whose status or body changes.
   - a caller that only calls the function for its side effect of raising (existence check).
4. Decide:
   - will_break: you can name the exact line and the exact wrong outcome for a realistic input.
   - might_break: it depends on data or a condition you cannot confirm from the code.
   - safe: it does not use the changed behaviour, or it already handles the new behaviour (for example an explicit `is None` check).
5. Rules:
   - The same signature does NOT mean safe. Python has no compiler to catch behaviour changes.
   - When unsure, choose might_break. Never choose will_break without naming the line and the outcome.
   - Never mark safe just because a test exists; tests may not cover the changed path.
   - A route (contract) whose status code or body changes for the same request is will_break.
6. Give a one-line reason (mention the line) and a one-line fix (the smallest change).

## Output (one JSON object per candidate)
{"id": "<candidate id>", "verdict": "will_break|might_break|safe", "reason": "<one line>", "fix": "<one line, empty for safe>"}

## Never
- Never edit files. Never invent callers that are not in the candidate list. Never read *.expected.json.
