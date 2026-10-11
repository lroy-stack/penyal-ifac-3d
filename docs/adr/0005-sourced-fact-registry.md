# 0005. Keep content as a sourced fact registry validated at build time

- Status: accepted
- Date: 2026-10-11
- Deciders: lr0y (product owner), tech lead

## Context
Accuracy matters more than the number of features. Research on 2026-10-10 found 11 facts where official sources disagree (tunnel length, route length, minors past the tunnel, Pobla church date, Silene category…) and several widely repeated claims that are false (e.g. "first natural park of the Comunitat"). The cards will be shown in three languages and must cite their sources and flag what is unverified.

## Options considered
1. **Fact registry (`content/sources.json`, `content/facts.json`) with a status per fact, validated by zod in the test suite; cards in F4 reference fact ids** — every number in the UI is traceable; conflicts are data, not prose.
2. **Free-text cards per language with footnotes** — quicker to write, impossible to audit automatically, and translations drift from each other.

## Decision
Option 1. Every fact has at least one value and every value cites at least one source (a missing figure is stated as such, e.g. "not published in the official sources consulted", and cites them). A fact is `verified` only with a single distinct value whose every entry cites an official source; `conflict` requires two or more different sourced values; `unverified` additionally requires a note. Orphan sources and unknown references fail the build.

## Consequences
- Cards (F4) show values from the registry with their sources and a visible label for `conflict` and `unverified`.
- Updating a fact is a data change with a reviewable diff; the park or the Ajuntament can review the registry directly.
- Each source records the access date and whether it was read from an archived copy, so stale data can be re-checked before release.
