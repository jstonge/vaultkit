"""Scaffold a new vault: config, templates, agent conventions and skills,
Obsidian settings, and an empty OKF bundle with its index.md and log.md.
Never overwrites a file that's already there."""

import shutil
import sys
from importlib.resources import files
from pathlib import Path

from . import okf
from . import vault as V

# where each scaffold folder lands in the new vault
RENAME = {"claude-skills": ".claude/skills", "obsidian": ".obsidian",
          "gitignore": ".gitignore"}
TEXT = {".md", ".toml", ".json", ".css", ""}


def init(args):
    dest = Path(args.dir).resolve()
    if (dest / "vault.toml").exists():
        sys.exit(f"{dest}/vault.toml exists; this is already a vault")
    tokens = {
        "__NAME__": args.name or dest.name,
        "__BUNDLE__": args.bundle,
        "__GROUP__": args.group_by,
        "__GROUP_LABEL__": args.group_by.replace("_", " ").capitalize(),
    }
    src = files("vaultkit") / "scaffold"
    made, kept = [], []

    def copy(node, rel):
        for child in node.iterdir():
            name = RENAME.get(child.name, child.name) if not rel.parts else child.name
            out_rel = rel / name
            if child.is_dir():
                copy(child, out_rel)
                continue
            out = dest / out_rel
            if out.exists():
                kept.append(out_rel)
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            if Path(child.name).suffix in TEXT:
                text = child.read_text(encoding="utf-8")
                for k, val in tokens.items():
                    text = text.replace(k, val)
                out.write_text(text, encoding="utf-8")
            else:
                shutil.copyfile(child, out)
            made.append(out_rel)

    copy(src, Path())
    v = V.load(dest)
    for t in v.templates.values():
        (v.bundle / t.folder).mkdir(parents=True, exist_ok=True)
    v.sources.mkdir(parents=True, exist_ok=True)
    if not (v.bundle / "log.md").exists():
        okf.log(v, "Creation", f"vault scaffolded by {V.TOOL_ACTOR}")
    okf.write_indexes(v)

    for p in made:
        print(f"  made  {p}")
    for p in kept:
        print(f"  kept  {p} (already there)")
    print(f"\n{dest}: OKF bundle at {args.bundle}/, notes grouped by `{args.group_by}`.")
    print("Open the folder as a vault in Obsidian, then enable Settings → Appearance →"
          " CSS snippets → agent-callout.")
