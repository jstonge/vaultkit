---
name: vault-curriculum
description: Work out, with the user, which reading notes need which others — the `requires:` edges that make the readings a graph, and the `key: true` papers — by interviewing them in rounds. Use this whenever the user wants to order the readings, decide what to read first, build a reading path or curriculum, find the prerequisites between notes, or mark the key papers. Distinct from vault-timeline, which orders by date rather than by what you need to understand first.
---

# Vault curriculum

The timeline puts the readings in the order they were published. This asks a
different question: what do you need to have read to follow this one? That
order is a graph, not a line — several notes can be readable at once, and
the reader picks. The edges are `requires:` on a reading note, and the papers
that matter most are `key: true`.

**The user decides every edge and every key.** Which notes belong together, and
in what order, is the thinking (`AGENTS.md`), and frontmatter can't carry an
`[!agent]` label the way prose does. So nothing goes into a note until the
user has said yes to it in chat, and you are the scribe. Never run
`vaultkit verify`.

You bring something they can't: you can read every note and its archive in
`sources/` and say what each one assumes. Your job is to propose, with the
evidence, and to disagree when the notes don't support what they say. A
curriculum agreed to on the first pass is usually one nobody decided.

## What an edge means

`A requires B` means: **a reader who hasn't read B will struggle with A.** Not
"related to", not "follows from in time", not "also worth reading". Test it
on each edge by naming what in A assumes something from B — a term it uses
without defining, a mechanism it builds on. If you can't name one, it isn't
an edge.

- **Keep it minimal.** If A requires B and B requires C, don't also write
  A requires C. The graph already says it, and a redundant edge makes the
  branch points look different than they are.
- **Point at what exists.** If A assumes something no note covers, that's a gap
  in the vault, not an edge. Report it in chat as a gap ("A assumes
  tokenization; nothing here covers it") and let the user decide whether to
  read something. Don't invent an edge to a note that merely sits nearby.
- **Dates don't make edges.** A newer post often requires an older one, but
  not always, and not only the older one.

## The loop

**0. Ask who it's for.** Before touching a note, ask what the reader already
knows. A note is "foundational" only relative to someone. The first reader is
a student picking up AI development; if the user says what they already know,
the notes that only teach that are roots, or aren't on the path at all. This is
the one thing the notes can't tell you.

**1. See what you have.**

```sh
vaultkit graph
```

Each reading note comes with its `level`, `key` and `__GROUP__`. Read the
`description:` of every note, and open the archive in `sources/` for any you
can't place. At the start nearly everything is level 0; that is the thing
you're fixing.

**2. Interview in rounds.** Work outward from what needs nothing. Each round
covers everything whose prerequisites are already settled, and never asks
about a note that depends on an answer you haven't heard.

- **Round 1: the roots.** Say which notes you'd treat as needing nothing else
  from the vault, and why, one line each. Ask which of those they'd change.
- **Round 2 and on: the frontier.** With the roots settled, ask which of the
  remaining notes become readable now. Propose edges for each — *B requires A
  because B uses …* — and ask. Ask for the nearest edge and not every distant
  one: if C needs B and B needs A, ask about C and B, not C and A.
- **Stop when every note is placed**: it's a root, or it has `requires:`, or
  the user has said it's off the path. Then ask what assumption you haven't
  stated.

Ask a handful of questions a round, each with your own answer and the reason
attached, so they can say "no, because…" instead of inventing one. Say which
you are least sure of. When they agree too easily, push once with the evidence,
then take their answer.

Questions about *feel* — does this sequence work, is this too much at once —
can't be settled by talking. Say so and suggest trying it on the first reader.

**3. Write each round down once it's agreed.** In the note that needs the
other, add the edge to its frontmatter:

```yaml
requires:
  - "[[reading/slug-of-the-prerequisite]]"
```

Quote the wikilink — unquoted, YAML reads `[[x]]` as a nested list and
`vaultkit check` rejects it. One list per note, a line per prerequisite. Touch
nothing else in the note: not `readStatus:`, not `verified`, not anything under
a `### <name>` heading. Then:

```sh
vaultkit check
```

It rejects an edge that points at no note and any loop. If it finds a loop,
say so — a loop usually means one edge is backwards, and the user should
choose which.

**4. Key papers, once the graph exists.** Ask separately, after the edges. A
key paper is one the user would tell the reader not to skip, and that is a
different question from what's a prerequisite: a note can be key without being
required by anything, and required by many without being key.

Propose candidates with a reason each. How many notes depend on it is a useful
pointer (it shows in `vaultkit graph`), but it isn't the answer; a note few
others require can still be the one that matters. The user says which. Set
`key: true` on exactly those, and leave the rest empty. When `key:` is set
on a note, check what its prerequisites are: a reader following only the key
notes still needs everything they require, which `vaultkit graph --key` shows.

**5. Show the result and ask what's wrong.**

```sh
vaultkit graph
vaultkit graph --canvas curriculum.canvas
```

Point out the branch points — notes sharing a level are a choice the reader
makes — and the ones that look too thin or too crowded. These are where the
choose-your-own-adventure parts live. Ask whether the order matches how the
user would actually teach it.

## Attribution

You write only what the user has approved, and the edges are theirs. When you
summarize the interview or the gaps in chat, say whose idea each was. Don't
leave an unlabelled paragraph about the curriculum in any note.

## What stays yours

Atomic notes at the bundle root, `## Thinking` sections, `readStatus:` and
`verified`. If the curriculum suggests a note should be split, retitled or
linked, say so in chat. A note that gathers the readings into a sequence is
the user's to write, not yours to generate.

## Keeping it current

When reading notes are added, only the new ones need a round: ask what each
requires and whether anything now requires it. Run `vaultkit check` after, and
regenerate the canvas. Don't revisit settled edges unless the user does.
