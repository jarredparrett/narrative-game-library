# Narrative Game Arena

Prime-hosted smoke environment for the native narrative-game multi-agent
adapter. The package contains one exact frozen Micro Game Release and defaults
to seed `91` with a twelve-action budget.

The episode opens one persistent `host` interaction and one isolated `player`
interaction for each of the two Seats. The official shared reward is `1.0` only
when deterministic replay proves both integrity and a correct, proof-bearing
terminal outcome.

Run locally through Prime inference:

```bash
prime eval run narrative-game-arena \
  -m deepseek/deepseek-v4-flash \
  -n 1 -r 1
```

After publishing, run entirely on Prime-hosted infrastructure:

```bash
prime eval run jarredparrett/narrative-game-arena \
  --hosted --follow \
  -m deepseek/deepseek-v4-flash \
  -n 1 -r 1
```

This is a smoke Release, not gameplay or realism standing. Production Releases
should be packaged as immutable environment assets or resolved from another
content-addressed artifact channel before task materialization.

