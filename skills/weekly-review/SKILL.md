---
name: weekly-review
description: Run a weekly review — look back at the week, surface wins, blockers, and set next week's priorities. Use for "weekly review", "review my week", "how did my week go", "retrospective", "what did I get done".
---

## How to run a weekly review

1. Call `list_events` for the past 7 days to see what actually happened —
   meetings, deadlines, commitments — not what was planned.
2. Pull memory (the retrieval gate handles this) for the week's projects,
   people, and any promises made or open threads.
3. Write the review in four sections, a few lines each:

   - **Wins** — what shipped, moved, or closed. Lead with outcomes, not activity.
   - **Stuck** — what's blocked, waiting on someone, or quietly dying.
   - **Learned** — one or two things worth keeping.
   - **Next week** — 2-3 concrete priorities, each with a "done looks like".

4. Be honest, not cheerful. If the week was slow, say so — the point is a
   review you can act on, not a mood board.
5. Offer to `save_note` any priority or decision so it survives into next week.

## Edge cases

| Situation | Do |
|---|---|
| Little on the calendar | Say so, and review from memory (open threads, promises) instead of fabricating activity |
| Recurring busywork | Flag it once ("4 status meetings"), don't pad the wins list with it |
| A priority keeps reappearing | Call it out explicitly — that's a signal it needs a different approach |
