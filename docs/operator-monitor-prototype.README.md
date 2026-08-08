# Operator evidence monitor UI prototype

**PROTOTYPE — THROW AWAY.** This answers one question: which information
hierarchy lets an operator understand trust, progress, uncertainty, budget,
incidents, and evidence lineage without mistaking a rebuildable projection for
canonical authority?

Run from the repository root:

```bash
python3 -m http.server 8116 --directory docs
```

Then open:

<http://127.0.0.1:8116/operator-monitor-prototype.html?variant=A&state=current>

Use the bottom switcher or left/right arrow keys to compare three structurally
different variants:

- `A` — Evidence Spine
- `B` — Coverage Plot
- `C` — Incident Workbench

Use the projection-state fixtures in the header to inspect `current`, `stale`,
`incomplete`, and `corrupt` behavior. The fixture is in-memory and every link is
inspection-only. The prototype does not read a Workspace, poll an agent, expose
sealed cases, or provide transition authority.

The chosen information model belongs on `main`. This full prototype remains on
the throwaway branch linked from the Wayfinder ticket.
