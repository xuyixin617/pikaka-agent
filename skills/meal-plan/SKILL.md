---
name: meal-plan
description: Plan meals for a week — recipes, a grocery list, and dietary preferences. Use for "meal plan", "what should I eat", "plan dinners", "grocery list", "meal prep", "what's for dinner".
---

## How to plan meals

1. Ask (or pull from memory) the constraints: how many people, how many meals,
   dietary needs (vegetarian, allergies, low-carb), budget, and how much time
   the user wants to spend cooking.
2. Propose a plan of dinners (and lunches if asked) for the days requested.
   Vary protein and cuisine so it doesn't feel repetitive.
3. For each meal, give a one-line idea and a short ingredient list — no full
   recipes unless asked.
4. Roll the ingredients up into a grocery list, grouped by section (produce,
   protein, pantry, dairy), with duplicates merged.
5. Note meals that share ingredients (roast chicken → chicken salad) so nothing
   goes to waste.

## Edge cases

| Situation | Do |
|---|---|
| No preferences given | Propose a balanced default, then ask if any foods are off-limits |
| Dietary restriction | Respect it absolutely; check every ingredient against it |
| Tight budget or time | Lead with cheap, fast staples (rice, eggs, beans, frozen veg) |
| Memory has their preferences | Apply them and mention it ("since you're vegetarian…") |
