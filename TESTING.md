# Testing & Reliability

## Full suite of test cases ran

The backend test suite is built using `pytest`. The following test cases passed and ensure the core scheduling engine behaves correctly:

1. **`test_cycle_detection`**: Verifies that adding a cyclic dependency (e.g., A -> B -> C -> A) throws a `CycleDetectedError` and accurately reports the path of the cycle.
2. **`test_self_dependency`**: Ensures a task cannot depend on itself (e.g., A -> A raises an error).
3. **`test_diamond_convergence`**: Validates a complex dependency graph (A -> B, A -> C, B -> D, C -> D). It checks that:
   - D starts only after both B and C finish.
   - If A slips and gets delayed, the delay accurately propagates downstream to shift D's start and end dates automatically.
4. **`test_rollback_status`**: Tests that if a prerequisite task (A) is marked as `DONE`, its dependent (B) is unblocked. If A is accidentally rolled back to `IN_PROGRESS`, B correctly becomes `blocked` again.
5. **`test_multi_level_propagation`**: Confirms that cascading schedules work sequentially across multiple levels (A -> B -> C -> D), ensuring dates are accurately offset down the chain based on the durations of each task.

## Known failure cases

Currently, there are **0** known failing test cases in the test suite (all 5/5 tests pass). However, there are a few architectural known limitations/edge-cases to be aware of:

1. **Weekend and Holiday Scheduling**: The scheduling engine currently calculates end dates using strict calendar days (e.g., adding `duration_days` directly to `start_date`). It does not yet skip weekends or holidays, meaning a 2-day task starting on Friday will end on Sunday, rather than Tuesday.
2. **Time Zones**: Dates are processed in UTC at the backend. If users in vastly different time zones create tasks near midnight, the "planned start date" might render off-by-one-day on the frontend due to localized browser rendering.
3. **Draft Suggestion Limits**: The AI auto-suggest draft feature does not currently have strict rate-limiting on the frontend. A user clicking the suggest button repeatedly before a request completes could queue multiple LLM API calls, though this only impacts UI performance.
