"""Render a note from a template and archive its source.

Articles are saved as readable markdown, YouTube links as a flattened
transcript, both under sources/. Summary text is read from stdin, so it never
has to survive shell quoting:

    vaultkit note https://example.com/post --slug author-short-title \\
        --description "One sentence." --tags a,b <<'EOF'
    Three to five sentences.
    EOF
"""

import re
import sys

from ruamel.yaml.comments import CommentedMap

from . import okf
from . import vault as V
from .archive import ALL_KINDS, IS_VIDEO, fetch, infer_kind


def add_arguments(ap, v):
    ap.add_argument("url", nargs="?", default="", help="omit for sources with no URL")
    ap.add_argument("--slug", required=True, help="filename, so the concept id; no .md")
    ap.add_argument("--title", default="", help="title: and the H1 (default: the slug)")
    ap.add_argument("--description", default="",
                    help="one sentence (default: the summary's first sentence)")
    ap.add_argument("--kind", choices=ALL_KINDS, help="default: inferred from the URL")
    ap.add_argument("--template", default="reading",
                    help=f"one of: {', '.join(v.templates)} (default: reading)")
    ap.add_argument("--tags", default="", help="comma-separated, appended and deduped")
    ap.add_argument("--added-by", default="",
                    help="who's adding the note (default: git user.name, else whoami)")
    ap.add_argument("--by", default="",
                    help="who made the source; comma-separated, links into who/")
    ap.add_argument(f"--{v.group_by}", dest="group", default="",
                    help=f"comma-separated; the {v.group_by}: field notes are grouped by")
    ap.add_argument("--model", default="",
                    help="model that wrote the summary, for generated.by "
                         "(default: $VAULT_MODEL)")
    ap.add_argument("--set", default=[], action="append", metavar="KEY=VALUE",
                    help="set any frontmatter key, e.g. --set recBy=Alice")
    ap.add_argument("--no-archive", action="store_true", help="skip the sources/ copy")
    ap.add_argument("--force", action="store_true", help="edit an existing note")


def names(csv):
    return [x.strip() for x in csv.split(",") if x.strip()]


def write_source(v, slug, url, text, how, published=None):
    copy = v.sources / f"{slug}.md"
    fields = CommentedMap()
    fields["type"] = "source"
    fields["title"] = f"{slug} (archived)"
    fields["description"] = f"Archived copy of {url}, fetched {V.today()}."
    fields["resource"] = url
    if published:
        fields["published"] = published
    fields["generated"] = CommentedMap(by=V.TOOL_ACTOR, at=V.now())
    fields["fetchedWith"] = how
    copy.parent.mkdir(parents=True, exist_ok=True)
    copy.write_text(V.dump(fields, f"\n{text}\n"), encoding="utf-8")
    return copy


def callout(summary):
    quoted = "\n".join(f"> {ln}" if ln.strip() else ">" for ln in summary.split("\n"))
    return f"> [!agent] {V.agent_name()} summary\n{quoted}"


def run(args, v, summary=None):
    t = v.templates.get(args.template)
    tpl = v.templates_dir / f"{args.template}.md"
    if t is None or not tpl.exists():
        sys.exit(f"no template {args.template!r}: needs [templates.{args.template}] in "
                 f"vault.toml and {tpl.relative_to(v.root)}")
    dest = v.folder(args.template) / f"{args.slug}.md"
    if dest.name in V.RESERVED:
        sys.exit(f"{dest.name} is reserved by OKF; pick another slug")
    if dest.exists() and not args.force:
        sys.exit(f"{dest.relative_to(v.root)} exists (use --force)")

    # re-running edits the note in place; the template is only the starting
    # point for a brand new one
    is_new = not dest.exists()
    fields, body = V.parse((tpl if is_new else dest).read_text(encoding="utf-8"))
    fields = fields if fields is not None else CommentedMap()
    title = args.title or (args.slug if is_new else str(fields.get("title") or args.slug))
    if is_new:
        for key, val in list(fields.items()):
            if val == "{{title}}":
                fields[key] = title
            elif val == "{{date}}":
                fields[key] = V.today()
        body = body.replace("{{title}}", title).replace("{{date}}", V.today())
    elif args.title:
        fields["title"] = title
        body = re.sub(r"(?m)^# .*$", lambda m: f"# {title}", body, count=1)
    fields.setdefault("type", args.template)  # OKF's one required key
    if not fields.get("title"):
        fields["title"] = title

    url = args.url
    copy = v.sources / f"{args.slug}.md"
    if t.archive and url and not args.no_archive:
        text, how, published = fetch(url)
        if text:
            print(write_source(v, args.slug, url, text, how, published)
                  .relative_to(v.root))

    # a re-run keeps the kind already on the note unless one is passed, so an
    # explicit --kind at creation isn't overwritten by a URL guess
    if t.archive and (is_new or args.kind):
        fields["kind"] = args.kind or infer_kind(url)
    # don't reattribute a note someone else already added
    author = args.added_by or V.identity()
    if args.added_by or not fields.get("addedBy"):
        fields["addedBy"] = author
    if args.group:
        fields[v.group_by] = V.seq(names(args.group))
    if args.by:
        # wikilinks so the property is clickable and shows in Obsidian's graph
        fields["by"] = V.seq(f"[[{b}]]" for b in names(args.by))
    if url:
        fields["resource"] = url
    if copy.exists():
        # OKF provenance, plus a wikilink because Obsidian can't click a path
        sources = [s for s in V.as_list(fields.get("sources"))
                   if not (isinstance(s, dict) and s.get("id") == "archive")]
        sources.insert(0, CommentedMap(id="archive", resource=f"/sources/{args.slug}.md",
                                       title="archived copy"))
        fields["sources"] = V.seq(sources)
        fields["localCopy"] = f"[[sources/{args.slug}|archived copy]]"
        # the page's own metadata; a date already on the note was put there
        # by someone who checked it, so it wins
        published = V.read(copy)[0].get("published")
        if published and not fields.get("published"):
            fields["published"] = str(published)
    for pair in args.set:
        if "=" not in pair:
            sys.exit(f"--set takes KEY=VALUE, got {pair!r}")
        key, val = pair.split("=", 1)
        fields[key] = val

    fresh = [x for x in names(args.tags) if x not in V.listed(fields, "tags")]
    if fresh:
        fields["tags"] = V.seq(V.listed(fields, "tags") + fresh)

    if summary:
        block = callout(summary)
        body = re.sub(r"(?m)^> \[!(?:claude|agent)\][^\n]*summary[^\n]*\n(?:>.*\n?)*\n*",
                      "", body)
        body, n = re.subn(r"(?m)^(# [^\n]*\n)\n*", lambda m: f"{m[1]}\n{block}\n\n",
                          body, count=1)
        if not n:
            body = f"\n{block}\n\n{body.lstrip()}"
        fields["generated"] = CommentedMap(by=V.agent_actor(args.model), at=V.now())
    if args.description:
        fields["description"] = args.description
    elif summary and not fields.get("description"):
        fields["description"] = V.first_sentence(summary)

    # a heading per author, so two people can write without editing the same
    # lines; only seeded on creation, never touched on a re-run
    if is_new and t.authored:
        body = re.sub(r"(?m)^(## [^\n]*\n)", lambda m: f"{m[1]}\n### {author}\n",
                      body, count=1)

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(V.dump(fields, body), encoding="utf-8")

    note = V.Note(dest, v.concept_id(dest), fields, body)
    if is_new:
        okf.log(v, "Creation", f"{okf.link(v, v.bundle, note)} — {args.template}, "
                               f"added by {fields.get('addedBy')}")
    elif summary:
        okf.log(v, "Update", f"{okf.link(v, v.bundle, note)} — summary rewritten "
                             f"by {fields['generated']['by']}")
    okf.write_indexes(v)
    print(dest.relative_to(v.root))
    return dest


def main(args, v):
    summary = "" if sys.stdin.isatty() else sys.stdin.read().strip()
    run(args, v, summary)
