# Problem and solution

A small change can preserve types while breaking callers' assumptions. Returning None instead of raising an exception can turn a useful 404 into a server error. Replacing dollars with integer cents can leave calculations syntactically valid while changing their meaning. Dependency upgrades can fail during test collection before ordinary test counts tell the whole story.

Uplift connects prediction to measured repair. A deterministic Python engine finds affected symbols, callers, API routes and mapped tests. Saved agent verdicts explain expected behavior changes. Proof tests must pass on the original code and fail on the changed code. Repairs run in isolated scenario copies, and the final suite verifies that the contracts are restored.

Impact mode includes conservative Docker instruction invalidation. Migration mode uses an official-guide catalog and checks added lines against observed naming, import and exception conventions. The Dash dashboard displays the graph, verdicts, proofs, repairs, before/after tests and missed predictions.

The sample shop contains three deliberately synthetic scenarios. S1 and S2 each have six reproduced contract failures and pass after repair. The Pydantic v2 scenario starts with eight test failures and six collection errors, then passes all 46 tests. S2's original predictions miss three dollar-unit contracts; its recall remains 0.50 even after those misses are repaired. No general accuracy claim is made beyond these fixtures.

IBM Bob supplied the original implementation and saved reasoning artifacts. Isolated repairs, integration, evaluation and final verification were completed using Bob modes. Reports state that provenance explicitly. Raw test output, JUnit XML, repair patches and reproduction scripts are included so every published number can be checked.

The dashboard runs locally and includes hosting configuration. A public deployment is not claimed. Existing Bob screenshots remain historical evidence; missing sessions are not fabricated.
