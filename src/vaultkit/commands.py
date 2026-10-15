"""The smaller commands: index, synth, verify, check."""

import argparse
import re
import sys
from pathlib import Path

from ruamel.yaml.comments import CommentedMap

from . import okf
from . import vault as V
from .note import names, run as run_note


# ---------------------------------------------------------------- index

def link_report(v, roots, reading_ids):
    """Per root note, (links in, links out, reading notes cited), plus groups
    of three or more root notes linked to each other with no note at the hub."""
    out_links = {n.id: V.links(v, n.path, n.body) for n in V.concepts(v)}
    ids = [n.id for n in roots]
    counts = {}
    for i in ids:
        incoming = sum(i in ls for src, ls in out_links.items() if src != i)
        outgoing = out_links.get(i, set()) - {i}
        counts[i] = (incoming, len(outgoing), len(outgoing & reading_ids))

    near = {n: {m for m in ids if m != n and (m in out_links[n] or n in out_links[m])}
            for n in ids}
    seen, clusters = set(), []
    for start in ids:
        if start in seen:
            continue
        group, todo = set(), [start]
        while todo:
            n = todo.pop()
            if n not in group:
                group.add(n)
                todo.extend(near[n] - group)
        seen |= group
        # a member that already links to every other one is the structure note
        hub = any(group - {n} <= out_links[n] for n in group)
        if len(group) >= 3 and not hub:
            clusters.append(sorted(group))
    return counts, clusters


def index(args, v):
    """Print what's already in the vault: the tag vocabulary, the groups
    covered, and one line per note — enough to pick existing tags and spot
    notes worth linking without reading every file."""
    if args.write:
        okf.write_indexes(v)
        print((v.bundle / "index.md").relative_to(v.root))
        return
    reading = V.notes_in(v, "reading") if "reading" in v.templates else []
    root_t = next((t.name for t in v.templates.values() if not t.folder), None)
    roots = V.notes_in(v, root_t) if root_t else []
    everything = V.concepts(v)
    if not everything:
        print("vault is empty")
        return

    tags = sorted({t for n in everything for t in V.listed(n.fields, "tags")})
    print("TAGS IN USE:", ", ".join(tags) or "(none)")

    if roots:
        counts, clusters = link_report(v, roots, {n.id for n in reading})
        print("\nYOUR NOTES (bundle root) — links in / out / reading notes cited:")
        width = max(len(n.slug) for n in roots)
        for n in roots:
            i, o, r = counts[n.id]
            print(f"  {n.slug:<{width}}  {i:>2} /{o:>2} /{r:>2}   {n.description}")
        checks = [
            ("nothing links here", [n.slug for n in roots if not counts[n.id][0]]),
            ("links nowhere", [n.slug for n in roots if not counts[n.id][1]]),
            ("cites no reading note", [n.slug for n in roots if not counts[n.id][2]]),
        ]
        if any(found for _, found in checks) or clusters:
            print("\n  to look at:")
            for label, found in checks:
                if found:
                    print(f"    {label}: {', '.join(found)}")
            for c in clusters:
                print(f"    linked, but no note gathers them: {', '.join(c)}")

    for name, t in v.templates.items():
        if t.folder and name != "reading" and (ns := V.notes_in(v, name)):
            print(f"\n{t.folder.upper()} ({len(ns)}):")
            print("  " + " · ".join(n.slug for n in ns))

    if authors := V.by_author(reading):
        print("\nBY AUTHOR:")
        width = max(len(a) for a in authors)
        for name, ns in authors.items():
            print(f"  {name:<{width}}  {len(ns)}")

    if grouped := V.groups(reading, v.group_by):
        print(f"\nBY {v.group_label.upper()}:")
        width = max(len(g) for g in grouped)
        for g, ns in grouped.items():
            kinds = ", ".join(sorted({str(n.fields.get("kind") or "?") for n in ns}))
            print(f"  {g:<{width}}  {kinds}")

    if pending := [n for n in everything if V.needs_review(n.fields)]:
        print(f"\nAGENT-WRITTEN, NOT YET VERIFIED BY A HUMAN ({len(pending)}):")
        print("  " + " · ".join(n.id for n in pending))

    if reading:
        print(f"\n{len(reading)} READING NOTES:")
        width = max(len(n.slug) for n in reading)
        for n in reading:
            label = f"[{n.fields.get('kind') or '?'}]"
            if gs := V.listed(n.fields, v.group_by):
                label += f"[{','.join(gs)}]"
            print(f"  {n.slug:<{width}}  {label:<24} {n.description}")


# ---------------------------------------------------------------- synth

def synth(args, v):
    """Bootstrap a synthesis note from what's already in reading/: one table
    row per group, with the reading notes on it linked. It writes no prose of
    its own — what each row says is yours (or the agent's) to add."""
    grouped = V.groups(V.notes_in(v, "reading"), v.group_by)
    if args.group:
        want = names(args.group)
        if missing := [g for g in want if g not in grouped]:
            sys.exit(f"no reading notes for: {', '.join(missing)}\n"
                     f"known: {', '.join(grouped)}")
        grouped = {g: grouped[g] for g in want}
    if not grouped:
        sys.exit(f"no reading notes carry a {v.group_by}: field yet")

    note_args = argparse.Namespace(
        url="", slug=args.slug, title=args.title, description=args.description,
        kind=None, template="synthesis", tags="", added_by="", by="",
        group=",".join(grouped), model=args.model, set=[], no_archive=True,
        force=args.force)
    dest = run_note(note_args, v)
    fields, body = V.read(dest)

    # labelled, because an unmarked survey reads as the user's own conclusion
    cols = list(v.synth_columns)
    block = [f"## By {v.group_label.lower()}\n",
             f"> [!agent] {V.agent_name()} survey",
             "> Assembled from the reading notes linked below. Argue with it under"
             " Thinking rather than editing it into agreement.\n",
             "| " + " | ".join([v.group_label, *cols, "Covered by"]) + " |",
             "| " + " | ".join(["---"] * (len(cols) + 2)) + " |"]
    for g, notes in grouped.items():
        links = " · ".join(okf.link(v, dest.parent, n).replace("|", "\\|") for n in notes)
        block.append(f"| **{g}** |" + "  |" * len(cols) + f" {links} |")
    block.append("")
    body = body.replace("## Sources\n", "")
    # a re-run replaces the survey rather than stacking a second one
    body = re.sub(rf"(?ms)^## By {re.escape(v.group_label.lower())}\n.*?(?=^## Thinking)",
                  "", body)
    body = body.replace("## Thinking\n", "\n".join(block) + "\n## Thinking\n", 1)
    fields["generated"] = CommentedMap(by=V.agent_actor(args.model), at=V.now())
    dest.write_text(V.dump(fields, body.rstrip("\n") + "\n"), encoding="utf-8")


# ---------------------------------------------------------------- verify

def verify(args, v):
    """Record that a person checked a note: appends {by, at} to `verified`.
    This is the human's attestation, so an agent never runs it for them."""
    path = Path(args.note)
    if not path.exists():
        path = v.root / args.note
    if not path.exists():
        # an archive shares its note's slug, and nobody verifies an archive
        hits = [n for n in V.concepts(v) if args.note in (n.slug, n.id)
                and n.fields.get("type") != "source"]
        if len(hits) != 1:
            found = ", ".join(n.id for n in hits) or "nothing"
            sys.exit(f"{args.note!r} matches {found}; pass the concept id")
        path = hits[0].path
    fields, body = V.parse(path.read_text(encoding="utf-8"))
    by = V.human_actor(args.by) if args.by else V.human_actor()
    if not by.startswith("human:"):
        sys.exit("verify records a person; agents don't verify notes")
    events = V.as_list(fields.get("verified"))
    events.append(CommentedMap(by=by, at=V.now()))
    fields["verified"] = V.seq(events)
    path.write_text(V.dump(fields, body), encoding="utf-8")
    note = V.Note(path, v.concept_id(path), fields, body)
    okf.log(v, "Verification", f"{okf.link(v, v.bundle, note)} — checked by {by}")
    print(path.relative_to(v.root))


# ---------------------------------------------------------------- check

def check(args, v):
    """OKF conformance: every concept has parseable frontmatter with a
    non-empty `type`, and index.md / log.md keep their shape. Warnings are
    things the spec recommends; only errors fail."""
    problems = okf.check(v)
    for level, path, msg in problems:
        if level == "error" or args.warnings:
            print(f"{level:<7} {path.relative_to(v.root)}: {msg}")
    errors = sum(1 for p in problems if p[0] == "error")
    warnings = len(problems) - errors
    tail = "" if args.warnings or not warnings else " (--warnings to list them)"
    print(f"{errors} error(s), {warnings} warning(s){tail}")
    sys.exit(1 if errors else 0)
