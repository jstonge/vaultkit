# vaultkit

The note-making tools from
[tales-from-the-agent-loop](https://github.com/jstonge/tales-from-the-agent-loop),
pulled out so any vault can use them, and rebuilt so the vault is also an
[Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
(OKF v0.2) bundle: markdown with YAML frontmatter that any OKF consumer can
read without knowing about Obsidian.

```sh
uv tool install --editable .        # from a checkout; or git+https://…
vaultkit init ~/vaults/new-vault --group-by topic
cd ~/vaults/new-vault && vaultkit index
```

Nothing in it calls a model. A skill is prose telling the agent what to do; a
command does only what doesn't need judgment — if it had to think, your notes
would depend on it thinking the same way twice.

## Commands

| command | |
| --- | --- |
| `vaultkit init DIR` | scaffold a vault: `vault.toml`, templates, `AGENTS.md`, skills, Obsidian settings, an empty bundle |
| `vaultkit note [URL] --slug S` | make or update a note from a template; archives the URL to `sources/`; summary on stdin |
| `vaultkit synth --slug S` | scaffold a survey table across reading notes, one row per group value |
| `vaultkit index` | print tags, groups, link counts and a line per note; `--write` rebuilds `index.md` |
| `vaultkit verify NOTE` | append `{by: human:<you>, at: now}` to the note's `verified` |
| `vaultkit check` | OKF conformance; exits 1 on errors, `--warnings` lists recommendations too |
| `vaultkit graph` | the prerequisite graph from `requires:` as JSON; `--key` keeps key notes and what they require; `--canvas FILE` writes an Obsidian canvas |
| `vaultkit timeline` | reading notes by `published:` as a Mermaid timeline with a dated link list |

`vaultkit <command> -h` has the flags. `note` keeps every flag `tools/note` had,
plus `--title`, `--description` and `--model`; `--harness` becomes
`--<group_by>`, whatever the vault's config names.

## How a vault is laid out

`vaultkit` finds the vault by walking up from the current directory to a
`vault.toml`, so it runs from anywhere inside one. The config names the OKF
bundle — a folder inside the vault — and keeps everything else outside it:

```
new-vault/
  vault.toml          which folders, templates and grouping field this vault uses
  AGENTS.md           conventions for agents; CLAUDE.md points here
  my-templates/       shared with Obsidian's Templates plugin
  .claude/skills/     vault-note, vault-synthesis, vault-review
  kb/                 the bundle — every .md here needs a `type:`
    index.md          generated; okf_version at the root
    log.md            generated; one bullet per creation, update, verification
    <atomic notes>    your own thinking
    reading/ synthesis/ who/ sources/   each with its own index.md
```

The bundle is a subfolder so that README, AGENTS.md and the templates never
have to pretend to be concepts. `bundle = "."` with an `exclude` list works
too, for a vault that already keeps notes at its root.

## How the fields map onto OKF

| field | OKF meaning | set by |
| --- | --- | --- |
| `type` | required; the template name: `reading`, `synthesis`, `who`, `atomic`, `source` | the template |
| `title`, `description` | display name; one-sentence summary that `index.md` shows | `--title`, `--description` (else the summary's first sentence) |
| `resource` | the URL a reading note is about | the URL argument |
| `sources` | provenance; the archived copy first | `note`, when it archives |
| `generated: {by, at}` | an agent wrote this, as `<agent>/<model>` | `note` / `synth` when there's a summary |
| `verified: [{by, at}]` | a person checked it, as `human:<id>` | `verify`, never an agent |
| `requires: ["[[reading/slug]]"]` | extension key: notes to read first; the edges of the curriculum graph | by hand, or an agent's draft you approve; `check` rejects dangling links and loops |
| `key: true` | extension key: a key paper | by hand |
| `kind`, `by`, `published`, `addedBy`, `readStatus`, `recBy`, `localCopy`, `date`, the group field | extension keys | as in tales |

`status` is OKF's lifecycle field (`draft`, `stable`, `deprecated`), so whether
someone has read a source moved to `readStatus`. Body links are relative
markdown links: OKF resolves them, and so does Obsidian, which reads a leading
`/` as the vault root rather than the bundle's. Wikilinks stay in frontmatter
(`by:`, `localCopy:`), where Obsidian needs them to be clickable and OKF
treats them as opaque extension values.

`$VAULT_AGENT` names the agent in callouts and `generated.by` (default
`Claude`), `$VAULT_MODEL` fills in the model when `--model` isn't passed, and
`$VAULT_HUMAN` overrides the `human:<id>` derived from `git config user.name`.

## Development

```sh
uv run pytest
```
