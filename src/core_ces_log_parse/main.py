#!/usr/bin/env python3
"""
core_ces_log_parse.main

Find log entries by sender email address, extract the MID(s), then collect all
log lines related to those MIDs and write them to output text file(s).

Assumptions / notes:
- Logs are plain text (one event per line).
- A "sender email address" can appear as:
    - addr=<user@domain>
    - from=<user@domain>
    - from=user@domain
    - sender=user@domain
    - mailfrom=<user@domain>
    - bare user@domain anywhere on the line
- A "MID" can appear as:
    - MID=12345
    - mid=12345
    - mid 12345
    - (if none of those exist, you can extend MID_REGEX)
- "Related to MID" means any line containing that MID token form (e.g. MID=12345)
  OR containing the bare number with a mid label; this script matches via regex.

Usage examples:
  # Extract all threads for specific senders from one or more log files into one output:
  python -m core_ces_log_parse.main \
    --logs input/mail1_1021.txt input/mail2_1021.txt \
    --senders input/addresses.txt \
    --out output/combined_threads.txt

  # Same, but write one output file per sender:
  python -m core_ces_log_parse.main \
    --logs input/mail1_1021.txt input/mail2_1021.txt \
    --senders input/addresses.txt \
    --outdir output/threads/

  # Provide senders inline:
  python -m core_ces_log_parse.main \
    --logs input/mail1_1021.txt input/mail2_1021.txt \
    --sender noreply@salesforce.com \
    --sender alerts@mail.salesforce.com \
    --out output/combined_threads.txt
"""

import argparse
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set

# Generic email regex (reasonable for logs; not fully RFC-complete by design)
EMAIL_REGEX = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)

# Common "sender-like" patterns in logs; we try these first for precision.
SENDER_FIELD_REGEXES = [
    re.compile(r"\baddr=<(?P<email>[^>]+@[^>]+)>", re.IGNORECASE),
    re.compile(r"\bfrom=<(?P<email>[^>]+@[^>]+)>", re.IGNORECASE),
    re.compile(r"\bfrom=(?P<email>[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})\b", re.IGNORECASE),
    re.compile(r"\bsender=(?P<email>[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})\b", re.IGNORECASE),
    re.compile(r"\bmailfrom=<(?P<email>[^>]+@[^>]+)>", re.IGNORECASE),
    re.compile(r"\bmail_from=<(?P<email>[^>]+@[^>]+)>", re.IGNORECASE),
]

# MID patterns to capture an identifier
MID_REGEX = re.compile(r"\b(?:MID|mid)\s*[:=]?\s*(?P<mid>\d+)\b")


@dataclass(frozen=True)
class LineRef:
    file: str
    lineno: int
    text: str


def load_senders(sender_files: List[str], sender_args: List[str]) -> Set[str]:
    senders: Set[str] = set(s.strip() for s in sender_args if s.strip())
    for path in sender_files:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    senders.add(line)
        except OSError as e:
            raise SystemExit(f"Error: could not read senders file '{path}': {e.strerror or e}")
    # Normalize to lowercase for matching
    return set(s.lower() for s in senders)


def extract_sender_candidates(line: str) -> Set[str]:
    cands: Set[str] = set()
    for rx in SENDER_FIELD_REGEXES:
        m = rx.search(line)
        if m:
            cands.add(m.group("email").strip().strip("<>").lower())
    # Fallback: any email in the line
    for m in EMAIL_REGEX.finditer(line):
        cands.add(m.group(0).lower())
    return cands


def extract_mid(line: str) -> Optional[str]:
    m = MID_REGEX.search(line)
    if not m:
        return None
    return m.group("mid")


def scan_mids_for_senders(senders: Set[str], log_paths: List[str]) -> Dict[str, Set[str]]:
    """
    First pass: For each sender, find the set of MIDs present on any line that mentions that sender.
    """
    sender_to_mids: Dict[str, Set[str]] = {s: set() for s in senders}

    for path in log_paths:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for raw in f:
                    line = raw.rstrip("\n")
                    cands = extract_sender_candidates(line)
                    if not cands:
                        continue

                    intersect = cands.intersection(senders)
                    if not intersect:
                        continue

                    mid = extract_mid(line)
                    if not mid:
                        # Sender appears but MID not on that same line. We do not guess here.
                        # If your logs have a separate correlation key, extend the script.
                        continue

                    for s in intersect:
                        sender_to_mids[s].add(mid)
        except OSError as e:
            raise SystemExit(f"Error: could not read log file '{path}': {e.strerror or e}")

    # Drop senders with no mids to keep output cleaner
    return {s: mids for s, mids in sender_to_mids.items() if mids}


def index_logs_for_mids(
    log_paths: List[str], mids_of_interest: Set[str]
) -> Dict[str, List[LineRef]]:
    """
    Second pass: Build an index of mid -> list of LineRef, but only for MIDs we care about.
    """
    mid_to_lines: Dict[str, List[LineRef]] = defaultdict(list)
    if not mids_of_interest:
        return mid_to_lines

    for path in log_paths:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for i, raw in enumerate(f, start=1):
                    line = raw.rstrip("\n")
                    mid = extract_mid(line)
                    if not mid or mid not in mids_of_interest:
                        continue
                    mid_to_lines[mid].append(LineRef(file=path, lineno=i, text=line))
        except OSError as e:
            raise SystemExit(f"Error: could not read log file '{path}': {e.strerror or e}")

    return mid_to_lines


def render_thread(
    sender: str,
    mids: Iterable[str],
    mid_to_lines: Dict[str, List[LineRef]],
) -> str:
    mids_sorted = sorted(set(mids), key=lambda x: int(x))
    out: List[str] = []
    out.append(f"=== SENDER: {sender} ===")
    out.append(f"MIDs: {', '.join(mids_sorted)}")
    out.append("")

    for mid in mids_sorted:
        out.append(f"--- MID {mid} ---")
        lines = mid_to_lines.get(mid, [])
        if not lines:
            out.append("(No lines found indexed by MID; check MID_REGEX.)")
            out.append("")
            continue

        # Keep original file/line context in case you need to trace back
        for ref in lines:
            out.append(f"[{os.path.basename(ref.file)}:{ref.lineno}] {ref.text}")
        out.append("")

    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Extract all log lines for message IDs (MIDs) by sender address."
    )
    ap.add_argument("--logs", nargs="+", required=True, help="One or more log file paths.")
    ap.add_argument(
        "--sender", action="append", default=[], help="Sender email address to match (repeatable)."
    )
    ap.add_argument(
        "--senders",
        action="append",
        default=[],
        help="Path to a file containing sender emails (one per line).",
    )
    ap.add_argument(
        "--out",
        default=None,
        help="Single output file (combined). Mutually exclusive with --outdir.",
    )
    ap.add_argument(
        "--outdir",
        default=None,
        help="Output directory (one file per sender). Mutually exclusive with --out.",
    )
    args = ap.parse_args()

    if bool(args.out) == bool(args.outdir):
        raise SystemExit("Error: Specify exactly one of --out or --outdir.")

    for path in args.logs:
        if not os.path.exists(path):
            raise SystemExit(f"Error: log file not found: {path}")

    for path in args.senders:
        if not os.path.exists(path):
            raise SystemExit(f"Error: senders file not found: {path}")

    senders = load_senders(args.senders, args.sender)
    if not senders:
        raise SystemExit("Error: No senders provided. Use --sender and/or --senders.")

    sender_to_mids = scan_mids_for_senders(senders, args.logs)

    if not sender_to_mids:
        raise SystemExit(
            "No matches found: none of the senders were found with a MID on the same line."
        )

    mids_of_interest: Set[str] = set()
    for mids in sender_to_mids.values():
        mids_of_interest.update(mids)

    mid_to_lines = index_logs_for_mids(args.logs, mids_of_interest)

    if args.outdir:
        try:
            os.makedirs(args.outdir, exist_ok=True)
        except OSError as e:
            raise SystemExit(
                f"Error: could not create output directory '{args.outdir}': {e.strerror or e}"
            )
        for sender, mids in sorted(sender_to_mids.items()):
            safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", sender)
            out_path = os.path.join(args.outdir, f"{safe}.txt")
            try:
                with open(out_path, "w", encoding="utf-8") as w:
                    w.write(render_thread(sender, mids, mid_to_lines))
            except OSError as e:
                raise SystemExit(
                    f"Error: could not write output file '{out_path}': {e.strerror or e}"
                )
        print(f"Wrote {len(sender_to_mids)} file(s) to: {args.outdir}")
    else:
        out_dir = os.path.dirname(args.out)
        if out_dir and not os.path.isdir(out_dir):
            try:
                os.makedirs(out_dir, exist_ok=True)
            except OSError as e:
                raise SystemExit(
                    f"Error: could not create output directory '{out_dir}': {e.strerror or e}"
                )
        try:
            with open(args.out, "w", encoding="utf-8") as w:
                for sender, mids in sorted(sender_to_mids.items()):
                    w.write(render_thread(sender, mids, mid_to_lines))
                    w.write("\n")
        except OSError as e:
            raise SystemExit(f"Error: could not write output file '{args.out}': {e.strerror or e}")
        print(f"Wrote combined output to: {args.out}")


if __name__ == "__main__":
    main()
