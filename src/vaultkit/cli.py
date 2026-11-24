"""vaultkit — notes for an Obsidian vault that is also an OKF bundle.

Run from anywhere inside a vault; the vault is the nearest directory up with a
vault.toml in it.
"""

import argparse
import sys

from . import __version__, commands, note
from . import vault as V
from .init import init


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    # `init` runs before there is a vault; everything else needs one, and the
    # note flags depend on its config (the group field names a flag)
    if argv[:1] == ["init"]:
        ap = argparse.ArgumentParser(prog="vaultkit init", description=init.__doc__)
        ap.add_argument("dir")
        ap.add_argument("--name", default="", help="default: the directory name")
        ap.add_argument("--bundle", default="kb", help="OKF bundle folder (default: kb)")
        ap.add_argument("--group-by", default="topic",
                        help="frontmatter list that groups reading notes (default: topic)")
        return init(ap.parse_args(argv[1:]))
    if argv[:1] in ([], ["-h"], ["--help"], ["--version"]):
        if argv[:1] == ["--version"]:
            print(__version__)
            return
        print(__doc__.strip() + "\n\ncommands: init, note, synth, index, verify, check, graph\n"
              "`vaultkit <command> -h` for each.")
        return

    v = V.load()
    ap = argparse.ArgumentParser(prog="vaultkit")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("note", help="make or update a note", description=note.__doc__,
                       formatter_class=argparse.RawDescriptionHelpFormatter)
    note.add_arguments(p, v)
    p.set_defaults(fn=note.main)

    p = sub.add_parser("synth", help="scaffold a survey across reading notes",
                       description=commands.synth.__doc__)
    p.add_argument("--slug", required=True)
    p.add_argument("--title", default="")
    p.add_argument("--description", default="")
    p.add_argument(f"--{v.group_by}", dest="group", default="",
                   help="comma-separated; default: all of them")
    p.add_argument("--model", default="")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=commands.synth)

    p = sub.add_parser("index", help="print what's in the vault",
                       description=commands.index.__doc__)
    p.add_argument("--write", action="store_true",
                   help="rewrite the bundle's index.md files instead")
    p.set_defaults(fn=commands.index)

    p = sub.add_parser("verify", help="record that a person checked a note",
                       description=commands.verify.__doc__)
    p.add_argument("note", help="path, concept id, or slug")
    p.add_argument("--by", default="", help="name or id (default: git user.name)")
    p.set_defaults(fn=commands.verify)

    p = sub.add_parser("check", help="OKF conformance", description=commands.check.__doc__)
    p.add_argument("--warnings", action="store_true", help="list warnings too")
    p.set_defaults(fn=commands.check)

    p = sub.add_parser("graph", help="the prerequisite graph as JSON",
                       description=commands.graph.__doc__)
    p.add_argument("--write", metavar="FILE", default="",
                   help="write to FILE instead of printing")
    p.set_defaults(fn=commands.graph)

    args = ap.parse_args(argv)
    args.fn(args, v)


if __name__ == "__main__":
    main()
