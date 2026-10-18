# Industry-Standard Git Protocols & Workflow Rules

Whenever starting a new prompt, task, or session, adhere strictly to the following industry-standard Git protocols:

## 1. Session / Task Start Protocol
- **Check Status & Context**: Inspect current branch, unstaged changes, and git state using `git status` and `git branch --show-current`.
- **Sync Remote Changes**:
  - Fetch updates from remote: `git fetch origin`.
  - When working on or branching from main/tracking branches, pull latest changes with rebase: `git pull --rebase origin <base-branch>`.
  - Avoid working directly on dirty or uncommitted state without stash or deliberate branching.

## 2. Branching Strategy
- **Never work directly on `main`** for feature work or experiments.
- **Branch Naming Conventions**:
  - `feat/<short-descriptor>` for features or extensions.
  - `fix/<short-descriptor>` for bug fixes.
  - `test/<short-descriptor>` for test suites and benchmark additions.
  - `refactor/<short-descriptor>` for structural changes without functional change.
- Ensure the active branch is verified before creating or editing files.

## 3. Frequent & Responsible Commits
- Commit in small, logical, atomic units as milestones or files are completed.
- Never do massive omnibus commits that mix unrelated changes.
- **Commit Message Format (Conventional Commits)**:
  - `<type>(<scope>): <concise present-tense description>`
  - Types: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`.
  - Provide an explanatory body summarizing additions/changes where appropriate.

## 4. Push Safety Directive
- **CRITICAL RESTRICTION**: Do **NOT** run `git push` to GitHub automatically or unprompted.
- All branching, fetching, rebasing, and commits are kept strictly local for review.
- Only run `git push` when the user explicitly instructs to push to remote.
