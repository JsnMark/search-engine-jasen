"""
dumpPartial.py

Debug tool: prints a binary partial index file (.pii) in readable form.

Usage:
    python3 dumpPartial.py out/myInvIndex_pii_0.pii              # every token
    python3 dumpPartial.py out/myInvIndex_pii_0.pii -t apple     # one token
    python3 dumpPartial.py out/myInvIndex_pii_0.pii -n 20        # first 20 tokens
    python3 dumpPartial.py out/myInvIndex_pii_0.pii --summary    # counts only
"""

import argparse

from posting import read_partial_record, deserialize_postings


def main():
    ap = argparse.ArgumentParser(description="Print a binary partial index file.")
    ap.add_argument("path")
    ap.add_argument("-t", "--token", help="only print this token")
    ap.add_argument("-n", "--limit", type=int, help="stop after this many tokens")
    ap.add_argument("--summary", action="store_true", help="only print totals")
    args = ap.parse_args()

    tokens = postings_total = printed = 0
    prev_token = None
    with open(args.path, "rb") as f:
        while (record := read_partial_record(f)) is not None:
            token, count, raw = record
            if prev_token is not None and token <= prev_token:
                print(f"!! not sorted: {prev_token!r} then {token!r}")
            prev_token = token
            tokens += 1
            postings_total += count

            if args.summary or (args.token and token != args.token):
                continue
            postings = deserialize_postings(raw)
            if len(postings) != count:
                print(f"!! {token!r}: header says {count} postings, decoded {len(postings)}")
            print(f"{token}  (df={count}, {len(raw)} bytes)")
            for p in postings:
                print(f"    did={p.did} tf={p.tf} title_tf={p.title_tf} "
                      f"important_tf={p.important_tf} positions={p.positions}")
            printed += 1
            if args.limit and printed >= args.limit:
                break
            if args.token:
                break

    print(f"-- {tokens} tokens read, {postings_total} postings")


if __name__ == "__main__":
    main()
