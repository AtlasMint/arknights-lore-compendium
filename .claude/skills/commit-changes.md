# Project-specific commit setup

This file is read by the personal `commit-changes` skill (`/commit-changes`) before it starts grouping and committing. Follow it in order, as a single gate that runs once before any commits are made — not per commit group.

For this project, use square brackets for the scoping. For example:
`git commit -m "fix[Monitoring]: showing all rows with scrollbar" -m "{optional body describing the bug and why it is fixed}"`