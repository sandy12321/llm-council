# llm-council

Ask every model in the room the same question, side by side.

`council.py` fans one prompt out to any number of OpenAI-compatible chat
endpoints concurrently and prints every answer with timings. `--verdict`
adds a deliberation round: the first member reads the rest and synthesizes
one conclusion, noting agreements and disagreements.

## Setup (keys stay out of the repo)

```sh
cp council.example.json council.json   # council.json is gitignored
export OPENAI_API_KEY="..."
export OPENROUTER_API_KEY="..."
```

Each member names the **environment variable** holding its token -- never
paste a key into a file.

## Use

```sh
python3 council.py --config council.json --prompt "Why is the sky blue?"
python3 council.py --config council.json --prompt "Best pasta shape?" --verdict
python3 council.py --prompt "smoke test" --dry-run   # no network, no keys
```

Exit code is 1 only if *every* member failed; partial answers still print.
One member's timeout or bad key never sinks the council -- failures arrive
as results, not exceptions.

## Test

```sh
python3 -m unittest -v
```

No dependencies, no network, no keys: HTTP is mocked at `urlopen`.

## Files

- `council.py` -- fan-out, verdict synthesis, CLI.
- `test_council.py` -- schema parsing, auth header, failure-as-data,
  ordering, dry-run, config loading.
- `council.example.json` -- copy to `council.json` and add your keys via env.
- `AGENTS.md` -- project conventions.
