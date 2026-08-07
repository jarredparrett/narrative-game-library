# Prime hosted multi-agent execution

`narrative_game_prime` is a native Verifiers v1 plugin for running a frozen Game
Release as a multi-agent Prime episode. It changes placement, not game authority.

## Ownership boundary

Prime owns model clients, harness/runtime placement, token traces, retries,
concurrency, evaluation upload, and the training loop. The narrative library
owns the authorized observation for each role, deterministic turn order, legal
tools, immutable Release, Session and arena hash chains, replay verification,
and the official reward.

The plugin declares two policy roles:

- `host`: one persistent host interaction;
- `player`: one shared policy definition, opened as a distinct persistent
  interaction for every Seat in the Release.

Thus six characters produce six private player traces, not one shared chat.
Each trace carries its exact narrative actor and role IDs. The host trace also
carries the canonical `EpisodeArchive`; `finalize()` rejects missing, duplicate,
or mismatched role traces before recording any reward.

## Reward

The adapter calls the library's `evaluate_episode()` exactly once. It records
the same `outcome_integrity` reward on every Prime trace:

```text
reward = integrity × outcome
```

Both factors are binary. Authorization, canonical evidence, replay, safety, a
correct terminal hypothesis, and a licensed proof path must all survive. Pacing,
participation, communication, objective progress, token attribution, and tool
efficiency are diagnostics; they do not dilute a successful result or rescue a
failed one.

## Run locally before spending hosted capacity

Install the adapter and use Prime inference while keeping the null harness local:

```bash
uv sync --extra prime
uv run eval narrative_game_prime \
  -m deepseek/deepseek-v4-flash -n 1 -r 1 -c 1 \
  --env.taskset.release-paths /absolute/path/game-release.zip \
  --env.taskset.episode-seeds 4100 \
  --env.host.model deepseek/deepseek-v4-flash \
  --env.player.model deepseek/deepseek-v4-flash \
  --sampling.max-tokens 1600 \
  --sampling.temperature 0 \
  --no-push
```

The default client uses `https://api.pinference.ai/api/v1` and authenticates via
`PRIME_API_KEY` or `prime login`. The output directory contains `config.toml`,
`traces.jsonl`, and the evaluation log. A completed host trace contains the
base64 canonical archive and structured reward report in `info`.

## Move every role to hosted Prime runtimes

After the local protocol smoke test passes, add:

```bash
--env.host.runtime.type prime \
--env.player.runtime.type prime
```

Each interaction then gets its own Prime runtime lifecycle. Use
`--env.max-concurrent-agents` to bound live agents inside one episode and `-c`
to bound episodes in flight. Their product is the maximum concurrent agent-run
pressure. Start with both values at `1`; increase only after observing latency,
rate limits, and spend.

## Publish the self-contained smoke environment

The repository includes `environments/narrative_game_arena`, a standalone Hub
package with the exact frozen Micro Game Release embedded as an asset. It proves
hosted packaging and execution without depending on a path from the machine
that submits the run.

```bash
prime env push \
  --path environments/narrative_game_arena \
  --visibility PRIVATE \
  --plain
```

After its managed Environment Action passes, launch it with:

```bash
prime eval run OWNER/narrative-game-arena \
  --hosted --follow \
  -m deepseek/deepseek-v4-flash \
  -n 1 -r 1
```

Prime requires the publishing account to choose a permanent public username
before its first Hub upload. That identity decision is account state, not an
environment setting, and should be made by the account owner.

## Train one role family at a time

Prime currently trains a single shared policy across the trainable traces in an
episode. The recommended progression is:

1. freeze the host and train all player Seat traces with
   `--env.train-host false --env.train-players true`;
2. evaluate on held-out Releases and seeds;
3. freeze the accepted player checkpoint and train the host with the flags
   reversed;
4. evaluate the combined lineup without changing the Release or reward contract.

Different host and player models are normal configuration. Role-local policy
and context IDs remain distinct in the canonical archive even when the underlying
model checkpoint is the same.

## What is and is not reproducible

The same Release, seed, models, sampling configuration, and returned actions
produce the same canonical Episode identity and bytes. Prime trace UUIDs,
wall-clock timings, and provider request IDs are operational metadata and are
not canonical identity. A model rerun may choose different actions; that is a
new episode sample, not nondeterminism in the environment.
