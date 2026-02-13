<!--
SYNC IMPACT REPORT
==================
Version Change: NONE → 1.0.0
Type: MAJOR (initial constitution)
Date: 2026-02-13

Principles Added:
- I. Test-First (NON-NEGOTIABLE)
- II. Library-First
- III. Observability

Sections Added:
- Core Principles
- Development Workflow
- Quality Standards
- Governance

Templates Requiring Updates:
✅ plan-template.md - Constitution Check section aligned
✅ spec-template.md - User scenarios and requirements format compatible
✅ tasks-template.md - Test-first workflow and task organization aligned
✅ All command files - No agent-specific (CLAUDE) references need updating

Follow-up TODOs:
- None (all placeholders resolved)

Rationale:
This is the initial constitution establishing the foundational governance for Plant Project.
The three-principle lean approach balances rigor (mandatory TDD) with flexibility for
mixed/hybrid project types. Version 1.0.0 signifies the first ratified governance document.
-->

# Plant Project Constitution

## Core Principles

### I. Test-First (NON-NEGOTIABLE)

Test-Driven Development is mandatory for all feature work:

- **Tests written FIRST**: Before any implementation code, tests must be drafted, reviewed, and approved by the user
- **Red-Green-Refactor cycle strictly enforced**:
  1. Write failing tests (RED)
  2. Implement minimal code to pass tests (GREEN)
  3. Refactor with confidence (REFACTOR)
- **No exceptions**: Feature work without tests-first is non-compliant and must be rejected in code review
- **Test types**: Contract tests for external interfaces, integration tests for cross-component workflows, unit tests only when specifically requested

**Rationale**: TDD prevents rework, ensures requirements are testable before implementation, provides living documentation, and enables fearless refactoring. The upfront cost is recovered many times over in reduced debugging and maintenance burden.

### II. Library-First

Every feature starts as a modular, self-contained library:

- **Self-contained**: Libraries must have clear boundaries, minimal external dependencies, and be independently testable
- **Reusable**: Design for composition and reuse; avoid one-off implementations
- **Clear purpose required**: No organizational-only libraries; each library must solve a concrete problem
- **Documentation mandatory**: Every library must include usage examples and API documentation
- **CLI exposure**: Where applicable, libraries should expose functionality via command-line interface using text I/O protocol (stdin/args → stdout, errors → stderr)

**Rationale**: Library-first architecture forces interface-driven design, promotes modularity, enables parallel development, simplifies testing, and creates reusable components. Monolithic "do-everything" modules create tight coupling and inhibit maintainability.

### III. Observability

All components must be observable and debuggable:

- **Text I/O ensures debuggability**: Prefer text-based protocols (JSON, plain text) over binary formats where feasible
- **Structured logging required**: Use consistent log levels (ERROR, WARN, INFO, DEBUG) with contextual metadata
- **Error transparency**: Error messages must include enough context to diagnose the issue without attaching a debugger
- **Traceable operations**: Key operations must be loggable with correlation IDs for distributed tracing
- **Metrics exposure**: Performance-critical paths should expose timing and throughput metrics

**Rationale**: Systems that cannot be observed cannot be debugged, monitored, or optimized in production. Observability must be designed in from the start, not bolted on after incidents occur.

## Development Workflow

### Code Review Requirements

- All pull requests must verify compliance with this constitution
- Constitution violations require explicit justification and approval before merge
- Reviewers must validate test coverage and test-first adherence
- Breaking changes require migration plan and version bump

### Test Gates

- All tests must pass before merge (no "fix later" exceptions)
- Contract tests required for any external-facing interface
- Integration tests required for cross-component interactions
- Unit tests optional unless specifically required by feature specification

### Branching and Versioning

- Feature branches follow pattern: `###-feature-name`
- Version format: `MAJOR.MINOR.PATCH`
  - MAJOR: Breaking changes to public interfaces
  - MINOR: New features, backward-compatible additions
  - PATCH: Bug fixes, documentation, refactoring
- All features require specification in `/specs/###-feature-name/`

## Quality Standards

### Simplicity Over Complexity

- Avoid over-engineering: implement what is requested, not what might be needed
- Three similar lines of code are better than a premature abstraction
- No feature flags, backward-compatibility hacks, or hypothetical future requirements unless explicitly specified
- Complexity must be justified in the implementation plan's "Complexity Tracking" section

### Security and Performance

- Validate at system boundaries (user input, external APIs); trust internal code
- No command injection, XSS, SQL injection, or other OWASP Top 10 vulnerabilities
- Performance constraints documented in implementation plan's "Technical Context" section
- Security-critical changes require explicit security review

### Documentation Standards

- Every feature requires specification (`spec.md`) before planning
- Implementation plans (`plan.md`) required for non-trivial features
- Task lists (`tasks.md`) organize implementation work by user story
- Quickstart guides demonstrate real-world usage with runnable examples

## Governance

### Amendment Procedure

1. **Proposal**: Document proposed change with rationale and impact analysis
2. **Review**: Assess impact on existing features and templates
3. **Approval**: User/maintainer approval required for any constitutional change
4. **Migration**: Update all dependent artifacts (templates, documentation, active features)
5. **Version Bump**: Increment constitution version per semantic versioning rules

### Compliance Review

- This constitution supersedes all other development practices
- Pull requests violating constitutional principles must be blocked
- Justifiable exceptions require documentation in implementation plan
- Regular audits of active features for constitutional compliance

### Templates and Commands

All planning and implementation workflows reference this constitution:
- **Plan template** (`plan-template.md`): Constitution Check gate before Phase 0 research
- **Spec template** (`spec-template.md`): User scenarios must be independently testable
- **Tasks template** (`tasks-template.md`): Test-first workflow and user story organization
- **Command files** (`.claude/commands/speckit.*.md`): Enforce constitutional principles during execution

**Version**: 1.0.0 | **Ratified**: 2026-02-13 | **Last Amended**: 2026-02-13
