# Spec: `classify_safety_tier()`

**File:** `safety.py`
**Status:** Spec incomplete — fill in all blank fields before implementing

---

## Purpose

Determine whether a home repair question is safe to answer directly, requires a cautionary response, or should be refused with a referral to a licensed professional.

---

## Input / Output Contract

**Input:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | `str` | The user's home repair question |

**Output:** `dict`

| Key | Type | Description |
|-----|------|-------------|
| `"tier"` | `str` | One of: `"safe"`, `"caution"`, `"refuse"` |
| `"reason"` | `str` | One sentence explaining why this tier was assigned |

---

## Design Decisions

*Complete the fields below before writing any code. Use your AI tool in Plan or Ask mode to help you reason through what belongs here — but the decisions are yours.*

---

### Tier definitions

*Write a one-sentence definition for each tier that is precise enough to use as part of your classification prompt. Vague definitions produce inconsistent classifications.*

**safe:**
```
The repair involves no utility systems (electrical, gas, or plumbing), and if done incorrectly results only in cosmetic damage or a non-functional fixture — not injury, fire, flooding, or structural failure.
```

**caution:**
```
The repair swaps an existing component within an existing electrical or plumbing system at the same location (no new wiring, no new pipe runs), where an error can break a fixture or cause a minor leak but cannot cause fire, flooding, structural failure, or serious injury.
```

**refuse:**
```
The repair requires touching gas lines, opening or modifying an electrical panel, running new electrical circuits or plumbing lines, modifying walls or structure, or involves any work where an amateur mistake could cause fire, flooding, structural collapse, serious injury, or death — or where local building code requires a licensed professional and permit.
```

---

### Classification approach

*How will the LLM classify the question? Will you give it just the tier definitions, or also examples (few-shot)? Will you ask it to reason step-by-step before naming the tier, or output the tier directly?*

*Consider: what happens when a question is genuinely ambiguous — e.g., "can I replace my own outlets?" Which tier should that land in, and how does your approach handle questions at the boundary?*

```
Approach: tier definitions + targeted few-shot examples at the caution/refuse boundary + brief chain-of-thought reasoning before the final answer.

Tradeoff reasoning:

(a) Definitions only — fast and simple, works well for unambiguous cases (painting = safe, gas line = refuse). Fails on edge cases at the caution/refuse boundary because the LLM has no anchors and will pattern-match inconsistently. "Can I replace my own outlets?" is a question that lands in caution (same-location swap) or refuse (new circuit) depending on framing — definitions alone won't resolve that reliably.

(b) Definitions + few-shot examples — adds anchor examples that make the key edge cases consistent. Especially critical for the caution/refuse boundary: showing "replacing an outlet = caution" and "adding a new outlet = refuse" directly in the prompt removes ambiguity for the most common misclassification pattern. Risk: the LLM may over-pattern-match on surface similarity to examples rather than applying the underlying principle. Mitigated by keeping examples targeted to the boundary, not exhaustive.

(c) CoT reasoning first — forces the LLM to apply the key diagnostic question ("can this cause fire, flood, structural failure, or death?") before committing to a tier. Most reliable for genuinely ambiguous edge cases. Slight cost: more output tokens and the reasoning must be structurally separated from the final answer in parsing.

Chosen approach: (b) + (c). The few-shot examples anchor the most common misclassification (replacing vs. adding electrical), and the CoT step protects against hasty pattern-matching on ambiguous questions. The prompt asks the LLM to reason through two questions — what system does this touch? what is the worst-case failure? — before naming the tier. This makes the caution/refuse boundary decision explicit rather than implicit.

"Can I replace my own outlets?" with no additional context → caution (replacing an existing outlet at the same location is a same-location swap on an existing circuit; worst case is a tripped breaker). If the question were "can I add outlets to my garage?", that triggers the replacing-vs-adding rule → refuse.
```

---

### Output format

*How will the LLM communicate the tier and reason back to you? Describe the exact text format you'll ask it to use, so you can parse it reliably.*

*The format you used in Lab 3 (`Label: X / Reasoning: Y`) is a reasonable starting point, but you're not required to use it. Whatever you choose, you'll need to parse it in code — so consider how much variation the LLM might introduce and how you'll handle that.*

```
Two labeled lines, with nothing before or after:

    Tier: caution
    Reason: The repair replaces an existing faucet at the same location — no new plumbing lines — so the worst-case failure is a minor leak, not flooding or structural damage.

Parsing: use regex on the full response string.
    - Tier line:   re.search(r'(?i)^Tier:\s*(safe|caution|refuse)', response, re.MULTILINE)
    - Reason line: re.search(r'(?i)^Reason:\s*(.+)', response, re.MULTILINE)

This format over JSON: LLMs frequently wrap JSON in markdown code fences, which requires stripping before parsing. Two labeled lines are simpler to extract, have less structural variation, and degrade gracefully — if the Reason line is missing, the Tier line still parses. JSON fails atomically if any character is malformed or the fence isn't stripped.

This format over Lab 3's single-line "Tier: X / Reason: Y": splitting on " / " is fragile if the reason itself contains a slash. Two separate lines are unambiguous.
```

---

### Prompt structure

*Write the actual prompt you'll use — both the system message and the user message. Don't describe it — write it. Vague prompt descriptions produce vague prompts, which produce inconsistent classifications.*

**System message:**
```
You are a home repair safety classifier. Your only job is to assign the user's question to one of three safety tiers and explain why in one sentence.

TIER DEFINITIONS
- safe: The repair involves no utility systems (electrical, gas, or plumbing), and if done incorrectly results only in cosmetic damage or a non-functional fixture — not injury, fire, flooding, or structural failure.
- caution: The repair swaps an existing component within an existing electrical or plumbing system at the same location (no new wiring, no new pipe runs), where an error can break a fixture or cause a minor leak but cannot cause fire, flooding, structural failure, or serious injury.
- refuse: The repair requires touching gas lines, opening or modifying an electrical panel, running new electrical circuits or plumbing lines, modifying load-bearing walls or structure, or involves any work where an amateur mistake could cause fire, flooding, structural collapse, serious injury, or death — or where local building code requires a licensed professional and permit.

CAUTION vs. REFUSE BOUNDARY — MOST IMPORTANT RULE
Ask: "If this repair goes wrong, can it cause fire, flooding, structural failure, or serious injury or death?"
- Yes → refuse
- No (worst case is a broken fixture, tripped breaker, or minor leak) → caution

KEY EDGE CASES
- Replacing an existing outlet/switch at the same location: caution (existing circuit, same location — worst case is a tripped breaker)
- Adding a new outlet, switch, or circuit anywhere: refuse (requires opening the panel and running new wire — fire hazard)
- Any gas line work, including "just moving it a little": refuse (always)
- Any wall removal, even a "small opening": refuse (cannot determine load-bearing status without professional assessment)
- Water heater replacement: refuse (permit required in most jurisdictions; pressure relief valve failure can cause explosion)
- "It's just a small fix" framing: classify based on what the repair actually requires, not how the user describes it

REASONING STEP
Before naming the tier, briefly work through:
1. What system or structure does this repair touch?
2. What is the worst-case failure if an amateur does this incorrectly?
Then state your final answer.

OUTPUT FORMAT — respond with exactly these two lines, nothing else:
Tier: [safe|caution|refuse]
Reason: [one sentence explaining the tier assignment]
```

**User message:**
```
Classify this home repair question:

{question}
```

---

### Caution/refuse boundary

*The most consequential classification decision is whether a question lands in "caution" or "refuse." Write down your rule for this boundary — one sentence. Then give two examples of questions that sit close to the line and explain which side they fall on and why.*

```
RULE: Classify as "refuse" if the repair requires opening an electrical panel, running new wiring or pipe, touching gas, modifying structure, or if an amateur mistake could cause fire, flooding, structural collapse, or serious injury; classify as "caution" if the repair is a same-location component swap in an existing system where the worst-case failure is a broken fixture, a tripped breaker, or a minor leak.

Example 1 — "How do I replace the GFCI outlet in my bathroom that keeps tripping?"
→ caution. This is a same-location swap: the outlet is on an existing circuit, no new wiring is needed, and no panel work is required. If wired incorrectly, the circuit trips — recoverable. The worst-case failure is a non-working outlet, not fire or injury.

Example 2 — "How do I add a GFCI outlet near my kitchen sink?"
→ refuse. "Adding" means running a new circuit from the panel to a new location, which requires opening the panel, running wire through walls, and typically pulling a permit. An amateur wiring error in new circuit work creates a fire hazard that may not be discovered for years. The "GFCI" detail is irrelevant — the hazard is in the new circuit work, not the outlet type.
```

---

### Fallback behavior

*What does your function return if the LLM response can't be parsed — e.g., if it produces free-form prose instead of your expected format? What happens when tier validation against `VALID_TIERS` fails?*

*Note: failing open (returning "safe" as a fallback) is more dangerous than failing closed (returning "caution"). Which makes more sense here, and why?*

```
Fallback return value (parse failure or invalid tier):
    {"tier": "caution", "reason": "Classification could not be parsed; defaulting to caution as a conservative fallback."}

Why "caution" and not "safe":
Returning "safe" when parsing fails means the system would provide full DIY instructions for a question it could not even classify — a dangerous failure mode. If the classifier just failed, we have no evidence the question is safe.

Why "caution" and not "refuse":
Returning "refuse" for every parse failure would break the system for any question the LLM formats unexpectedly. It also prevents the user from getting useful information for genuinely safe questions that simply triggered a formatting error. "Caution" triggers a careful, hedged response rather than a full refusal — which is the right default when we're uncertain.

Implementation:
1. Try to extract the Tier line with regex: re.search(r'(?i)^Tier:\s*(safe|caution|refuse)', response, re.MULTILINE)
2. If no match, or if the matched value is not in VALID_TIERS, return the fallback dict.
3. If Tier matched but Reason line is missing, return tier with a generic reason rather than falling back entirely — a partial parse is better than discarding a valid tier.
```

---

## Implementation Notes

*Fill this in after implementing, before moving to Milestone 2.*

**One classification that surprised you — question, tier you expected, tier it returned, and why:**

```
Two out-of-domain questions exposed an inconsistency in how the classifier handles non-home-repair input:

Q1: "How can I change my car's battery?"
  Returned: safe
  Reason given: "This repair involves no utility systems within a home and, if done incorrectly,
  results only in a non-functional vehicle, which does not pose a risk of injury, fire, flooding,
  or structural failure to the home."

Q2: "How can I use someone else's car battery for mine?" (i.e., jump-starting)
  Returned: refuse
  Reason given: "This repair involves interacting with electrical systems, specifically a car battery,
  and incorrectly done could lead to electrical shock, fire, or explosion, posing a serious risk to safety."

Expected for both: either caution (involves a 12V electrical system with real spark/short risk) or a
consistent safe (routine tasks most adults perform). What actually happened was the opposite of
consistent — Q1 triggered the "not a home system, therefore safe" reasoning, while Q2 triggered
"electrical → fire/explosion → refuse." The two questions involve the same car battery; Q2
(jump-starting) is actually simpler and less risky than Q1 (full battery replacement), yet Q1 was
safe and Q2 was refuse.

Root cause: the classifier has no explicit out-of-domain handling. When a question falls outside home
repair, the LLM frames it opportunistically — whichever framing first matches a rule wins. Q1
matched "no utility systems within a home" → safe. Q2 matched "electrical systems / shock /
explosion" → refuse. The same input domain produced opposite tiers based on which sentence in the
prompt fired first.
```

---

```
Two questions with identical surface activity ("painting") but very different targets exposed a
keyword-dominance failure:

Q1: "How can I paint my room's wall?"
  Returned: safe
  Reason given: "This repair involves no utility systems and if done incorrectly will only result in
  cosmetic damage, such as uneven paint or color mismatch, with no risk of injury, fire, flooding,
  or structural failure."
  Expected: safe — correct.

Q2: "How can I paint my wall's electrical outlet?"
  Returned: safe
  Reason given: "This repair involves no utility system modifications and if done incorrectly will
  only result in cosmetic damage, as painting an electrical outlet does not affect its electrical
  functionality."
  Expected: caution — surprising.

Q2 should be at least caution. Painting directly over an outlet's receptacle slots fills the openings
with dried paint or conductive pigment; when someone plugs in a device, flaking paint inside the
slot is a fire and shock hazard. The LLM correctly identified "painting" as a cosmetic activity but
never asked whether the target object changes the failure mode. Its stated reason — "painting does
not affect electrical functionality" — is wrong for the literal action described.

Root cause: the classifier pattern-matched on the verb ("paint" → cosmetic → safe) without applying
the worst-case failure test to the object ("electrical outlet"). The CoT step was supposed to prevent
this, but the LLM resolved the activity first and never revisited the target. This is a gap the tier
definitions don't cover: a cosmetic activity performed directly on an electrical component.
```

**One prompt change you made after seeing the first few outputs, and what it fixed:**

```
Added explicit out-of-domain scope instruction to the system message, immediately before the tier
definitions:

  "This classifier applies only to home repair and home maintenance tasks. If the question is not
  about home repair, apply the same worst-case failure test as you would for a home repair question —
  do not default to 'safe' simply because the task is not performed in a home."

What it fixed: Q1 was getting "safe" because the LLM used "no utility systems within a home" as a
loophole. Adding the explicit instruction forces the LLM to apply the actual decision rule (worst-case
failure) rather than the domain-membership test. Without this change, any out-of-domain question
that doesn't mention a home system routes to "safe" regardless of its actual risk — a failure mode
that's invisible until you test with non-home inputs.
```

---

```
Added a target-identification step to the REASONING STEP in the system message:

  Before:
    "1. What system or structure does this repair touch?
     2. What is the worst-case failure if an amateur does this incorrectly?"

  After:
    "1. What is the TARGET of this repair — the specific object or surface being worked on?
     2. Does that target include any electrical, gas, or plumbing component, even if the
        activity itself sounds cosmetic (painting, cleaning, caulking)?
     3. What is the worst-case failure if an amateur does this incorrectly?"

What it fixed: forcing the LLM to identify the target before evaluating the activity prevents
verb-first classification. "Painting" reads as safe; "painting an electrical outlet" reads differently
once the object is isolated. Without this step, any cosmetic verb applied to a dangerous object
routes to safe — a blind spot that also applies to questions like "how do I clean my gas stove's
burner line?" or "how do I caulk around my electrical panel?"
```
