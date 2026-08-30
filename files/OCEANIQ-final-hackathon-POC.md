# OCEANIQ
## Catching Illegal Oil Spills at Sea — Explained Simply

---

## The Problem

Ships sometimes illegally dump oil waste into the ocean instead of disposing of it properly. This pollutes the sea, harms marine life, and damages coastal economies.

The hard part isn't just spotting the oil — it's proving **which ship did it**. By the time anyone notices a spill, the ship has usually moved on. And ships that are dumping illegally often deliberately switch off their location tracker to avoid getting caught.

**The government (NTRO) wants a system that uses satellite images and ship-tracking data together to catch oil spills and point to the likely culprit.**

---

## Our Idea, In One Sentence

**We work backward, like a detective:** find the oil spill → figure out where and when it most likely started by tracing it back through the ocean currents and wind → then check which ships were actually near that spot at that time → and explain, step by step, why we suspect the ship we suspect.

We deliberately do **not** just say "there's a ship nearby, must be them" — that's too easy to get wrong, and it's what most simple approaches do. Our whole pitch is doing the "backward reconstruction" properly instead of skipping it.

---

## How It Works, Step by Step

**1. Spot the spill using special radar images**
Regular satellite photos need daylight and clear skies. We instead use **radar satellite images (called SAR)**, which work at night and through clouds — exactly the conditions when illegal dumping is most likely to happen, since it's easier to get away with it.

**2. Make sure it's actually oil**
Some natural things on the ocean surface — like algae, calm patches of water, or light rain — can look like an oil spill in radar images. We add a filter to rule these out, so we're not chasing false alarms.

**3. Measure the spill**
Once confirmed, we measure its size, shape, and direction — useful clues for the next step.

**4. Trace it backward in time**
This is the core of our idea. Oil spills drift with wind and ocean currents after they happen. We use an existing, trusted ocean-science simulation tool (called OpenDrift, used by real researchers) to run the spill's movement **backward in time** — figuring out roughly *where* and *when* it most likely started, not just where it ended up.

**5. Check which ships were actually there**
Ships are required to constantly broadcast their location (this signal is called AIS — think of it like a ship's GPS beacon). We pull historical ship location data for that estimated time and place, and see which ships were actually in the area.

**6. Score each nearby ship on multiple clues, not just one**
For every candidate ship, we check several things:
- Was it in the right place?
- Was it there at the right time?
- Was it moving in a direction consistent with the drift?
- Did its tracker (AIS) mysteriously go quiet during that window?

Each of these adds points to a transparent score — so instead of a vague "94% sure," we can show exactly *why* a ship is our top suspect.

**7. Show it all on a simple dashboard**
A map showing the spill, the estimated origin area, and the ship tracks — with a ranked list of suspects and a clear explanation for each.

---

## What Already Exists (Being Honest About It)

We're not claiming to invent something nobody has thought of before:

- **CleanSeaNet**, run by the European Maritime Safety Agency, already does something similar for European waters — satellite detection, ship tracking, and drift analysis to catch polluters.
- Researchers have already published studies doing versions of this, including some using satellite data over Indian waters.
- Some public tracking tools already flag ships that suspiciously switch off their tracker.

So a judge could reasonably ask "hasn't this been done already?" — and the honest answer is yes, in pieces, elsewhere in the world.

---

## So What Makes Ours Different?

| What others typically do | What we do instead |
|---|---|
| Just detect the oil spill | Detect it **and** measure its shape and direction |
| Say "the nearest ship is guilty" | Actually trace the spill backward to find where it *started*, and check who was there **then** — not just who's nearby **now** |
| Flag a missing tracker signal as automatic proof of guilt | Treat a missing signal as **one clue among several**, not proof by itself — because trackers can also fail or have gaps for innocent reasons |
| Give one vague confidence number | Show a clear breakdown: which specific clues pointed to this ship, and how strongly |

Our honest pitch: **we're not inventing new ocean science — we're combining existing, trusted tools into a system that explains its reasoning clearly, instead of jumping to conclusions.** That's a more defensible, more useful system than a black box that just says "trust the AI."

---

## What We're Actually Building (and What We're Skipping)

**Building for the demo:**
- Spill detection from a real satellite radar image
- Filtering out false alarms
- Backward drift tracing using the established OpenDrift tool
- Matching ship location history against the estimated spill origin
- A clear, explainable scoring and ranking system
- A dashboard to show all of this visually

**Skipping for now (future work, not needed to prove the idea):**
- Live, real-time monitoring of the whole coastline
- A fully automatic "this ship is 100% guilty" verdict — we produce leads for human investigators, not final judgments
- Anything requiring expensive, non-public data

---

## The Demo

We show one real (or realistic) example spill from start to finish:

1. Satellite spots a spill
2. System confirms it's really oil, not a false alarm
3. System calculates where and when it likely started
4. System pulls up which ships were near that spot at that time
5. System ranks the ships and explains why the top one is the most likely suspect

That's the entire story — simple to follow, but backed by real reasoning at every step, not guesswork.

---

## One Honest Limitation to Mention Upfront

We can point to the **most likely** ship based on the available evidence — we can't claim 100% certainty. Think of it like a detective narrowing down suspects with strong evidence, not a court verdict. That's exactly why we show our reasoning instead of hiding it behind one confidence number — it's meant to help human investigators focus their attention, not replace them.
