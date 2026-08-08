# Incident analysis prototype

Throwaway UI prototype for the Wayfinder ticket
[Prototype contrasting agentic incident analyses](https://github.com/jarredparrett/narrative-game-library/issues/41).

Run it with one command from the repository root:

```bash
python3 -m http.server 8115 --bind 127.0.0.1 --directory docs
```

Then open:

<http://127.0.0.1:8115/incident-analysis-prototype.html?variant=A&case=rescue>

Use the bottom switcher or the left/right arrow keys to compare three structural
variants. Use the case switch to compare the missing rescue transition with the
passing-but-host-dependent handoff.

This prototype is intentionally not production code. Event addresses in the
two compact fixtures illustrate the decided evidence contracts and are not a
replacement for the original archived traces.
