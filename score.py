"""Score an AI tool's answers against the golden answers.

Usage: python score.py <golden.csv> <answers.csv>
answers.csv has the header qid,answer,note (note is ignored). Two-part answers
are written "label | number". Prints a markdown scorecard; exits 0 only if
every answer matches, 2 if the golden file is not proven by both sources.
"""
import csv, re, sys
from datetime import datetime

NUM = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?(?:[eE][-+]?\d+)?")


def num(s):
    m = NUM.search(s)
    return float(m.group().replace(",", "")) if m else None


def same(a, g):
    return a is not None and abs(a - g) < 0.006


def label(s):
    s = s.strip().casefold()
    for f in ("%Y-%m", "%B %Y", "%b %Y"):
        try: return datetime.strptime(s, f).strftime("%Y-%m")
        except ValueError: pass
    return s


def match(answer, golden):
    if not answer.strip():
        return False
    if "|" not in golden:
        return same(num(answer), num(golden))
    (al, _, an), (gl, _, gn) = answer.partition("|"), golden.partition("|")
    return label(al) == label(gl) and (not an.strip() or same(num(an), num(gn)))


if __name__ == "__main__":
    rd = lambda p: list(csv.DictReader(open(p, newline="", encoding="utf-8-sig")))
    gold, ans = rd(sys.argv[1]), {r["qid"]: r["answer"] or "" for r in rd(sys.argv[2])}
    bad = [g["qid"] for g in gold if g["raw_agrees"] != "yes"]
    if bad:
        print("[FAIL] golden answers not proven by both sources: " + ", ".join(bad))
        sys.exit(2)
    ok = [match(ans.get(g["qid"], ""), g["golden"]) for g in gold]
    esc = lambda s: s.replace("|", "\\|")
    print(f"**Score: {sum(ok)} / {len(gold)}**\n\n| # | Question | Answer | Golden | Match |\n|---|---|---|---|---|")
    for g, m in zip(gold, ok):
        print(f"| {g['qid']} | {esc(g['question'])} | {esc(ans.get(g['qid'], ''))} | {esc(g['golden'])} | {'yes' if m else 'NO'} |")
    sys.exit(0 if all(ok) else 1)
