# 15-Minute City

## How This Started

One day I was ordering something from Amazon Fresh when a random thought hit me — how long would it actually take me to just go out, walk to the nearest grocery store, pick up everything I need, and come back?

It sounds like a simple thing, but it’s something we do all the time.

So I checked it on Google Maps.

And then I tried the same for a friend who lives in a different area.

The difference was… not small.

For me, it was manageable. For him, it was almost a task you’d have to plan for.

And that’s when it clicked — this isn’t just about groceries. The same applies to hospitals, parks, pharmacies, and pretty much everything we consider “basic”.

That’s when I came across a concept by Carlos Moreno called the **15-minute city**.

---

## What is the 15-Minute City?

The idea is simple enough to explain in one line:

You should be able to access most of your daily needs within 15 minutes of where you live.

Not by driving across the city, but by walking or cycling.

This includes:

- groceries
- healthcare
- education
- parks
- everyday services

Cities like Paris have already started working toward this model, restructuring neighborhoods to make them more self-sufficient.

---

## Why This Actually Matters

Once you think about it, a lot of what we call “busy life” is just time spent getting from one place to another.

If basic things are far away:

- you depend more on vehicles
- small tasks take longer than they should
- your day gets shaped around distance

But if things are nearby:

- life feels simpler
- time becomes more predictable
- neighborhoods feel more complete

This difference is subtle, but it affects daily life a lot more than we usually notice.

---

## What This Project Tries to Do

After that initial curiosity, I wanted to look at this in a more concrete way.

Not just “this area feels convenient” — but actually measure it.

So this project tries to answer:

- From a given location, what can you realistically reach within 15 minutes?
- Are essential services actually accessible, or just geographically close?
- Which areas are well-served, and which clearly are not?

---

## How It Works

The idea is implemented in a fairly structured way:

1. The city is modeled as a network
   - locations are nodes
   - roads are connections

2. From a starting point, all reachable areas within 15 minutes are calculated
   - this forms an isochrone (a realistic reachable region)

3. The system checks what exists inside that region
   - hospitals, stores, services, etc.

4. A score is assigned based on availability of essentials

5. Everything is visualized on a map
   - with careful layering so that roads remain visible and the data stays readable

---

## Tech Stack

This project uses:

- Graph-based modeling for reachability
- Spatial data handling
- Time-based calculations instead of simple distance
- Map visualization with layered rendering

The focus was on making the output meaningful rather than just building features.

---

## Challenges

Some things that turned out to be harder than expected:

- Distance doesn’t always reflect accessibility
- Real-world data is incomplete and inconsistent
- Deciding what counts as “essential” is subjective
- Map overlays can easily become messy if not handled carefully

A lot of time went into refining these aspects.

---

## References

- Carlos Moreno — 15-minute city: https://www.researchgate.net/publication/362839186_Definition_of_the_15-minute_city_WHAT_IS_THE_15-MINUTE_CITY
- Paris initiative: https://www.paris.fr/dossiers/paris-ville-du-quart-d-heure-ou-le-pari-de-la-proximite-37
- ChatGPT
- DeepSeek (for brainstorming)

---

## Final Thoughts

This started as a small curiosity about something as basic as buying groceries.

But once you look at cities through this lens, it changes how you see them.

You start noticing what’s nearby, what’s missing, and what feels unnecessarily far.

That’s really what this project is about.
