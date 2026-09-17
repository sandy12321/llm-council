"""llm-council -- ask every model in the room the same question.

Point it at any OpenAI-compatible chat endpoint, fan the prompt out to
all council members concurrently, and get every answer back with timings.
Optional ``--verdict`` asks the first member to synthesize the rest into
one conclusion (a council that deliberates).

Keys never live in files: each member names an environment variable that
holds its bearer token. ``--dry-run`` answers without touching the
network, so the pipeline is testable with zero credentials.
"""

import concurrent.futures
import json
import os
import sys
import time
import urllib.request

DEFAULT_TIMEOUT = 60


def load_config(path):
    """Load {"members": [{"name", "endpoint", "model", "key_env"}]}."""
    with open(path) as fh:
        return json.load(fh)["members"]


def ask_member(member, prompt, timeout=DEFAULT_TIMEOUT, dry_run=False):
    """Ask one member; always return a result dict, never raise."""
    name = member.get("name", "?")
    if dry_run:
        return {"name": name, "ok": True, "text": f"[dry-run] {name} heard you.",
                "seconds": 0.0}
    key = os.environ.get(member.get("key_env", ""), "")
    if not key:
        return {"name": name, "ok": False,
                "text": f"missing env var {member.get('key_env')!r}",
                "seconds": 0.0}
    body = json.dumps({
        "model": member["model"],
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        member["endpoint"].rstrip("/") + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"},
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.load(resp)
        text = payload["choices"][0]["message"]["content"]
        return {"name": name, "ok": True, "text": text,
                "seconds": time.time() - started}
    except Exception as exc:  # network, auth, schema -- all become data
        return {"name": name, "ok": False, "text": f"{type(exc).__name__}: {exc}",
                "seconds": time.time() - started}


def convene(members, prompt, timeout=DEFAULT_TIMEOUT, dry_run=False,
            max_workers=None):
    """Ask all members concurrently; results in config order."""
    with concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers or max(1, len(members))) as pool:
        futures = [pool.submit(ask_member, m, prompt, timeout, dry_run)
                   for m in members]
        return [f.result() for f in futures]


def verdict_prompt(question, answers):
    """Build the synthesis prompt for the deliberation round."""
    parts = [f"Question: {question}\n",
             "Fellow council members answered:"]
    for a in answers:
        parts.append(f"\n--- {a['name']} ---\n{a['text']}")
    parts.append("\nSynthesize the above into one short verdict. "
                 "Note where they agree and where they disagree.")
    return "\n".join(parts)


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description="Ask a council of LLMs one question.")
    ap.add_argument("--config", default="council.json")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--verdict", action="store_true",
                    help="first member synthesizes the rest")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    members = load_config(args.config)
    print(f"Council convened: {', '.join(m['name'] for m in members)}\n")
    results = convene(members, args.prompt, args.timeout, args.dry_run)
    for r in results:
        status = f"({r['seconds']:.1f}s)" if r["ok"] else "(FAILED)"
        print(f"--- {r['name']} {status} ---\n{r['text']}\n")
    if args.verdict and any(r["ok"] for r in results):
        print("--- deliberation ---")
        v = ask_member(members[0],
                       verdict_prompt(args.prompt, [r for r in results if r["ok"]]),
                       args.timeout, args.dry_run)
        print(v["text"])
    failed = sum(not r["ok"] for r in results)
    return 1 if failed == len(results) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

