# Brand assets

## `positioning-statement`

The pitch in one image.

```
Traffic  D̶a̶t̶a̶
Traffic  M̶o̶n̶i̶t̶o̶r̶i̶n̶g̶
Traffic  Intelligence
```

**The focus has moved.** The strikethroughs do not say data and monitoring are worthless —
**Siliguri can manage both.** They say those tiers are handled, and attention now belongs
on the one that is missing.

Read it as *"past this, past this, **here**"* — not as *"wrong, wrong, right"*. That
distinction matters in the room: a city that has invested in data and monitoring has built
the foundation this layer stands on, and the pitch should never sound like it says
otherwise.

| File | Use |
|---|---|
| `positioning-statement.svg` | **Source of truth.** Edit this, never a PNG |
| `positioning-statement@1x.png` | 1024×768 — documents, email |
| `positioning-statement@2x.png` | 2048×1536 — decks, retina |
| `positioning-statement@4k.png` | 3840×2880 — projection, wall display |

### Palette

| Role | Hex | Meaning |
|---|---|---|
| Ground | `#000000` | — |
| Retained | `#FFFFFF` | The constant: *Traffic* |
| Struck | `#E0392B` | The tiers that already exist |
| **Signal** | `#F5E76B` | **What we build** — the only warm colour, used once |

The yellow appears exactly once in the whole composition. That is the point of it.

### Regenerate

```bash
rsvg-convert -w 2048 -h 1536 positioning-statement.svg -o positioning-statement@2x.png
```

Typeface is Helvetica Neue Bold with Arial fallback, so it renders identically without a
font licence. Text is live in the SVG — searchable, translatable, and accessible via
`aria-label`.
