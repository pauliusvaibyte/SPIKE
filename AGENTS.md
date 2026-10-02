# AGENTS.md — SPIKE / QuantLab falsification harness

## Verification Doctrine

Tests are evidence, not deliverables. Optimize for proving the requested behavior works, not for test count, coverage, snapshots, mocks, or a green suite.

- Prefer E2E / broad-stack tests as the primary acceptance mechanism. Exercise the real public interface, real internal components, real persistence, and realistic state whenever practical.
- Do not choose the easiest E2E scenario. Choose the smallest realistic medium-to-hard scenario with high discriminating power: multiple interacting behaviors, meaningful state transitions, important boundaries, and persisted/external outcomes.
- E2E is primary, not exclusive. Use focused/property/invariant/contract/fuzz/state-machine tests only when they detect an important failure class substantially better than E2E.
- Before isolated testing or implementation, enumerate how the behavior could realistically fail. Design verification against those failure modes first.
- Tautological tests are harmful. Never derive expected results from the implementation, duplicate the same algorithm in the test, or copy actual output into expected output.
- Change-detector tests are harmful. Test externally meaningful behavior, not private structure, internal call ordering, implementation details, or mocks that merely restate the code.
- Internal mocks require justification. Prefer real owned components. Mock/fake genuine external boundaries only when necessary for safety, determinism, cost, or controlled fault injection.
- Do not backfill unit tests after implementation merely to claim coverage. A post-hoc test is valuable only if its oracle is independent and it can demonstrably reject a plausible broken implementation.
- Do not automatically add regression tests for bug fixes. Reproduce the bug first, identify the missing behavioral invariant, then strengthen the broader verifier. Preserve a bug-specific test only when it covers a genuine behavioral gap.
- Verify the verifier. For important features, temporarily remove/bypass/corrupt a critical part of the implementation. The acceptance test must fail for the expected reason. Restore it and verify PASS.
- Preserve some verification independence when practical. Use held-out composition scenarios, independently generated inputs, invariants, or immutable fixtures so implementation cannot simply optimize against every visible test.
- Coverage and mutation scores are diagnostics, not proof. Mutation testing answers whether the verifier notices certain faults; it does not prove the oracle itself is correct.
- Important E2E runs must produce a repeatable evidence artifact: reproduction command, inputs/fixtures, seed if relevant, machine-readable result, important persisted/output state, logs/traces, environment/version information, and hashes where useful.

Before declaring substantial work complete, answer:

1. What realistic incorrect implementation would this verification reject?
2. Could I remove or bypass the feature and still pass?
3. Could I satisfy the tests without actually delivering what the specification requested?

If #2 or #3 is yes, verification is insufficient.

Never optimize for passing the verifier. Optimize for satisfying the specification, and treat the verifier as an incomplete attempt to detect when you have not.
