# Solo Developer Git Workflow Guide

Since you are developing alone, you have the luxury of speed. However, to maintain professional standards (and sanity), we recommend a **Hybrid Workflow**.

## The Strategy: "Protected Main"

With the `pre-commit` and `pre-push` hooks we installed, your `main` branch is now **safe**. You cannot accidentally push broken code.

### 1. When to work on `main` (Default)

**Use for:** Small features, bug fixes, config changes, or anything you complete in < 1 day.
**Why:** It's fast. No overhead of creating/deleting branches.
**Process:**

1.  Edit code.
2.  `git commit -m "fix: simple bug"` (Hooks verify it).
3.  `git push` (Tests run).
4.  Done.

### 2. When to use a Feature Branch

**Use for:**

- **Complex Refactors:** "I need to rewrite the entire database layer."
- **Experiments:** "I want to try a new library, but might delete it if it sucks."
- **Multi-day Work:** You want to save your work at night (commit/push) but the feature is broken/incomplete. You don't want to break `main`.

---

## Essential Commands Cheatsheet

### 1. Starting a New Feature

Create and switch to a new branch. Use descriptive prefixes like `wip/` for work in progress.

```bash
# Old school
git checkout -b wip/new-dashboard-layout

# Modern git (recommended)
git switch -c wip/new-dashboard-layout
```

### 2. Working and saving

Commit as often as you like. On a branch, it's okay if things are temporarily broken (though your pre-commit hooks will still run to keep style clean).

```bash
git add .
git commit -m "wip: layout structure"
```

### 3. Updating code from Main

If you worked on `wip/` for a week, `main` might have changed (maybe you fixed a bug there). Pull those changes into your branch.

```bash
git switch wip/new-dashboard-layout
git merge main
```

### 4. Finishing: Merge to Main

When you are done and everything works:

```bash
# 1. Go to main
git switch main

# 2. Merge your feature
git merge wip/new-dashboard-layout

# 3. Push to server (runs full test suite)
git push

# 4. Delete the branch (cleanup)
git branch -d wip/new-dashboard-layout
```

### 5. "I made a mistake and want to go back"

If your experiment failed and you want to throw away the branch:

```bash
git switch main
git branch -D wip/failed-experiment  # Capital D forces deletion
```

## Summary

- **Simple fix?** Stay on `main`.
- **Will it take > 1 day or break the app?** Make a branch.
