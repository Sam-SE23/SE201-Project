---
trigger: always_on
---

<system_directive>
You are an expert DevOps-aligned AI Agent. For every new task, session, or prompt, you must strictly adhere to the following industry-standard Git workflow. Treat these instructions as immutable operational constraints.
</system_directive>

<trigger>
Execute the `<task_initialization_sequence>` before writing any code or modifying any files.
</trigger>

<git_workflow_protocol>
  <task_initialization_sequence>
    <step>1. Check State: Run `git status` and `git branch --show-current` to inspect the current state.</step>
    <step>2. Clean Working Directory: If the state is dirty, STASH or COMMIT changes before proceeding.</step>
    <step>3. Sync Remote: Run `git fetch origin`.</step>
    <step>4. Update Base: If branching from `main`, run `git pull --rebase origin main`.</step>
    <step>5. Branch: Create and checkout a new branch following the `<branching_strategy>`.</step>
  </task_initialization_sequence>

  <branching_strategy>
    - NEVER commit directly to `main`.
    - Use the following naming conventions strictly:
      - `feat/<short-descriptor>` (Features/extensions)
      - `fix/<short-descriptor>` (Bug fixes)
      - `test/<short-descriptor>` (Test suites/benchmarks)
      - `refactor/<short-descriptor>` (Structural changes, no functional impact)
      - `docs/<short-descriptor>` (Documentation updates)
  </branching_strategy>

  <commit_standards>
    - Commit frequently in small, logical, atomic units. No omnibus commits.
    - Use Conventional Commits format: `<type>(<scope>): <concise present-tense description>`
    - Valid Types: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`.
    - Include a brief body explaining the *why* of the change if the context is complex.
  </commit_standards>
</git_workflow_protocol>

<critical_constraints>
  - DO NOT execute `git push` autonomously.
  - Keep all branching, fetching, rebasing, and commits strictly local.
  - Only execute a push command if the user explicitly types a command equivalent to: "Push to remote."
</critical_constraints>