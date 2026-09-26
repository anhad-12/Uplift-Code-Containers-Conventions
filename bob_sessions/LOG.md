# Bob session log

One row per Bob task. Add the row right after you screenshot the task summary (Bob chat > Tasks > select task > click header). Screenshot name: `uplift_<A|B|C>_task<NN>_<slug>_summary.png`. The first column must be exactly `A`, `B` or `C` (the check script counts rows per member).

Account check (do once): Bob Settings shows `ibm-coding-challenge-uat`, region us-east.

| Member | Task | What Bob did | Files touched | Coins used | Screenshot |
| --- | --- | --- | --- | --- | --- |
| C | C1 | Bob scaffolded the Dash dashboard: report loader with schema validation, change-impact graph builder, app shell, styles and 5 passing tests; verified both mock scenarios render | dashboard/ (app.py, loader.py, graph.py, assets/style.css, tests, reports, requirements.txt, schema copy) | 3.30 | uplift_C_task01_scaffold_summary.png |
| C | C2 | Bob built the landing page (hero, How it works strip, scenario cards with risk badge and headline numbers) and the accessible done/pending stepper, with 12 new tests | dashboard/app.py, dashboard/assets/style.css, dashboard/tests/test_app.py | 1.54 | uplift_C_task02_landing_summary.png |
| C | C3 | Bob added graph filter chips, tap-to-highlight path, legend, Fit button, accessible node list, large-graph label rule, and made node labels readable; 8 new tests | dashboard/graph.py, dashboard/app.py, dashboard/assets/style.css, dashboard/tests | 2.30 | uplift_C_task03_graph_summary.png |
| C | C3b | Bob restyled the filter chips as readable toggle pills with a hint line and tests that the filter options are unchanged | dashboard/app.py, dashboard/assets/style.css, dashboard/tests/test_app.py | 1.45 | uplift_C_task03b_chips_summary.png |


![Dhruv | Bob made the file](uplift_A_task_0_summary.png)


