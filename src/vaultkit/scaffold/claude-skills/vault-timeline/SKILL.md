---
name: vault-timeline
description: Build a timeline note in `synthesis/` that puts the reading notes, and the events around them, in date order — a Mermaid timeline with the readings linked underneath. Use this whenever the user asks for a timeline, a history, what happened when, how the field got here, or wants the readings placed in time. Distinct from vault-synthesis, which compares by __GROUP__ rather than by date.
---

# Vault timeline

A reading note says what one source claims. A timeline says where it sits: what
came before, what it was answering, what followed. It's the first half of a
curriculum — chronology — before anyone argues about what depends on what.

These land in `__BUNDLE__/synthesis/`, not the bundle root. The root is for the
user's own thinking, and a generated timeline there would blur that.

`vaultkit timeline` does the part that doesn't need judgment: sort the reading
notes by `published:`, group them by year, make the text safe for Mermaid, and
link each note. You do the rest — which events belong beside the readings, and
what the order shows.

## The loop

**1. See what you have.**

```sh
vaultkit timeline
```

It prints a Mermaid block and a dated list of links. The count on stderr is
the notes with no usable `published:` — they're listed at the bottom, not in
the diagram.

**2. Check the dates before you build on them.** A date from page metadata is
a guess. Be suspicious of a documentation page or a repo, whose date is more
often the last edit than a publication; the `vault-note` skill says to leave
`published:` empty for those. Read the archive in `sources/` for anything that
looks off. Say in chat which dates you doubt and why; fix one with
`vaultkit note … --force --set published=YYYY-MM-DD` only when the archive
shows the right date. For the undated, ask the user rather than guessing.

**3. Decide what else belongs.** The timeline is of events; the readings are
the evidence for some of them. A reading about the Model Context Protocol
sits beside "MCP announced". Three kinds of event, and what each needs:

- **A reading note's own date.** Already in the diagram; nothing to add.
- **An event a reading or its archive states** — "released in March", a
  version number. Add it as an extra period and name the note it came from.
- **An event from your own knowledge or a web search.** Say so, with the date
  you looked it up, per `AGENTS.md`. A funding round or a release date goes
  stale in a way an archive doesn't. Ask the user before adding more than a
  few; the timeline is theirs to curate.

Fewer events, each placed on purpose, beat a chronicle of everything.

**4. Create the note.**

```sh
vaultkit note --template synthesis --slug <slug> --title "<title>" \
    --model <your model id> --no-archive \
    --description "One sentence: what the timeline shows." <<'EOF'
Three to five sentences on what the order shows: what the earliest readings
were responding to, where the field turned, what's missing from the record.
EOF
```

That text goes under a `> [!agent] <name> summary` banner. Write what the
dates reveal, not a description of the diagram.

**5. Put the diagram in its own section.** Don't nest it in the summary
callout. Open the note and, above `## Thinking`, add:

```
## Timeline

> [!agent] <name> timeline
> Assembled from `published:` on the reading notes, plus the events marked
> below. Argue with it under Thinking rather than editing it into agreement.

<the vaultkit timeline output, with any events you added>
```

Mermaid draws periods in the order written, so keep new events in date order.
Mermaid has no escape for `:` — write ` - ` instead. An event can't link, so
every period you add also gets a line in the list below the diagram, with the
note it came from or `(looked up YYYY-MM-DD)`.

**6. Say what's missing.** Name the undated notes, the long gaps, and the
stretches the vault has nothing on. A thin year says as much about the
reading as about the field.

**7. Run `vaultkit check`.**

## Attribution

Everything you put in the note sits under a `> [!agent] <name>` banner. See
`AGENTS.md`. Never run `vaultkit verify` — that's the user saying they've
checked the timeline against its sources.

## What stays yours

`## Thinking` is the user's, under their `### <name>` heading. Never write
there. Which events matter, and whether the order tells a story, is the
thinking; put it in chat as an observation.

## Keeping it current

When reading notes land or dates change, run `vaultkit timeline` again and
replace the diagram and list under `## Timeline`. Re-add any events you'd
marked by hand — the command knows only the readings. Don't re-run
`vaultkit note --force` for this: it rewrites the summary and isn't needed.
