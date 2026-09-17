# Project instructions

- Dependency-free Python. Standard library only.
- Keep implementation in `council.py`, tests in `test_council.py`.
- Run `python3 -m unittest -v` after changing Python files.
- Never accept API keys in files, arguments, or code -- env vars only.
  `council.json` (real config) is gitignored; only `council.example.json`
  is committed.
- Failures (network, auth, schema) are returned as result dicts, never raised.
- Do not commit, push, or publish anything unless explicitly requested.
- In the final response, distinguish checks actually run from suggested checks.
