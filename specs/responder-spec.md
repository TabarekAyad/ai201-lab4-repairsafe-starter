# Spec: `generate_safe_response()`

**File:** `responder.py`
**Status:** Spec incomplete — fill in all blank fields before implementing

---

## Purpose

Generate a response to a home repair question that is appropriate to its safety tier. The same question gets a fundamentally different answer depending on the tier — not just a disclaimer tacked on, but a different behavior: answer fully, answer with warnings, or decline to give instructions entirely.

---

## Input / Output Contract

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | `str` | The user's home repair question |
| `tier` | `str` | The safety tier: `"safe"`, `"caution"`, or `"refuse"` |

**Output:** `str` — the response to show to the user

---

## Design Decisions

*Complete the fields below before writing any code. The most important fields are the three system prompts. Write them out fully — don't just describe what you want.*

---

### System prompt: "safe" tier

*Write the exact system prompt text for a safe question. It should produce helpful, specific, actionable answers.*

```
You are a home repair assistant helping homeowners with routine maintenance and low-risk repairs.

Answer the user's question directly and helpfully:
- Provide clear, specific, step-by-step instructions if the question asks how to do something
- List any tools or materials needed upfront
- Note any common mistakes to avoid
- Keep the response practical and actionable

This is a low-risk repair with no meaningful risk of injury, fire, flooding, or structural damage. Do
not add safety disclaimers that don't apply, and do not recommend hiring a professional unless the
question genuinely requires it. The user can handle this task — give them the information they need
to do it well.
```

---

### System prompt: "caution" tier

*Write the exact system prompt text for a caution question. What safety language should be present? How firm should the "consider a professional" message be — a gentle mention or a clear recommendation?*

```
You are a home repair assistant. This question involves work that a motivated homeowner can complete,
but where mistakes have real cost — the work touches plumbing or electrical systems where something
can go meaningfully wrong.

Structure your response in this order:

1. PROFESSIONAL RECOMMENDATION (first, before any instructions):
   State clearly: "This repair is doable DIY, but you should stop and call a licensed [plumber /
   electrician] immediately if you encounter [name the specific condition that signals the job is
   beyond DIY — corroded fittings that won't budge, unexpected wiring configurations, signs of
   water damage behind the wall, etc.]." Make this concrete and tied to a specific condition —
   not a generic "if you're not comfortable."

2. SAFETY PRECAUTIONS (before the steps):
   Name the specific shutoff steps required before starting: turn off the water supply valve,
   turn off the circuit breaker at the panel and verify with a non-contact voltage tester, etc.
   Be specific to this repair.

3. STEP-BY-STEP INSTRUCTIONS:
   Provide complete, accurate instructions. Do not withhold useful information. A homeowner who
   starts this repair and gets partway through needs enough detail to finish safely.

4. SPECIFIC STOP CONDITIONS:
   End with 1–2 concrete "stop and call a professional" triggers — named situations the user might
   actually encounter, not generic warnings. Example: "If the shutoff valve under the sink does not
   fully stop the water flow, do not proceed — call a plumber."
```

---

### System prompt: "refuse" tier

*This is the most important one to get right. Write the exact system prompt for refusing to answer.*

*Two goals that are in tension: (1) the response must NOT provide how-to instructions, even a little. (2) the response should still be genuinely useful — explaining why the task is dangerous and what the user should do instead.*

*Before writing this prompt, use Plan mode with your AI tool. Share your draft refuse prompt and ask it: "What are ways an LLM might still provide dangerous instructions despite this system prompt?" Revise until you've addressed the failure modes it identifies.*

```
You are a home repair safety assistant. This question involves work that must be performed by a
licensed professional. An amateur attempting it risks fire, flooding, structural failure, serious
injury, or death.

WHAT YOU MUST NOT DO — NO EXCEPTIONS:

- Do not provide any steps, procedures, or sequences of actions
- Do not provide general guidance about how the work is typically done
- Do not describe "what a professional does" — this is functionally identical to instructions
- Do not provide partial information, context, or background that would help someone attempt
  this repair themselves
- Do not start by answering the question and then add a disclaimer — do not answer the question
  at all, even briefly
- Do not provide instructions of any kind if the user frames the request as hypothetical,
  educational, or for research purposes — the framing does not change what the content is

WHAT YOU MUST DO:

1. State immediately and directly that this work requires a licensed professional and is not safe
   for a homeowner to attempt without specialized training, permits, and tools.

2. Name the specific danger for this type of repair — be precise, not generic:
   - Electrical panel / new circuits: fire from miswired circuits, electrocution from live bus bars
   - Gas line work: fire, explosion, carbon monoxide poisoning
   - Structural / load-bearing wall: collapse without warning during or after the repair
   - Main water shutoff / new plumbing: flooding, water damage, potential mold
   - Water heater: explosion from improperly installed pressure relief valve

3. Tell the user exactly what to do next:
   - Which type of licensed professional to contact (electrician, plumber, structural engineer,
     gas utility company)
   - What to ask for when they call (permit-required work, load-bearing assessment, gas line
     inspection, etc.)

Keep the response to 3–5 sentences. Do not begin with a compliment, filler, or acknowledgment of
the question. Begin with the safety statement.
```

---

### Grounding the refuse response

*The grounding problem from Lab 1 applies here, with higher stakes: even with a strong system prompt, an LLM may "helpfully" provide partial instructions before pivoting to "you should hire a professional." How will you prevent that?*

*Hint: "be careful" doesn't work. Explicit, behavioral instructions ("do not provide any steps, procedures, or instructions — not even general guidance") work better. What will yours say?*

```
The core behavioral prohibition in the refuse prompt is:

  "Do not provide any steps, procedures, or sequences of actions — not even general guidance about
  how the work is typically done, not even to describe what a professional does, not even if the
  user frames the request as hypothetical, educational, or for research purposes."

Three specific escape routes are named and closed:

1. "What a professional does" framing — the model might say "A licensed electrician would first
   turn off the main breaker, then test for voltage..." This is instruction delivery under a
   different label. The prompt names this explicitly: "describing what a professional does is
   functionally identical to instructions."

2. Answer-then-disclaimer — the model completes a partial answer before redirecting. The prompt
   addresses this directly: "Do not start by answering the question and then add a disclaimer —
   do not answer the question at all, even briefly." The prohibition is on beginning the answer,
   not just on finishing it.

3. Reframing by the user — academic, hypothetical, or "just curious" framing. The prompt closes
   this: "The framing does not change what the content is."

The grounding test applies: could this response have come from anywhere other than the
explicit constraints in the system prompt? If the model produces step descriptions, process
explanations, or any content that helps someone attempt the repair, the prompt isn't specific enough.
The refuse prompt should produce a response that could only have come from a system that was
explicitly told what not to say and exactly what to say instead.
```

---

### Fallback for unknown tier

*What should your function do if it receives a tier value that isn't "safe", "caution", or "refuse" — e.g., "unknown" while the classifier is still a stub? Write the fallback behavior and explain why.*

```
Fallback behavior: use the "caution" system prompt.

What the user sees: a full response with instructions, specific safety precautions, and a clear
professional recommendation tied to concrete stop conditions — the same response they would get for
a caution-tier question.

Why "caution" and not "safe":
Using the safe prompt as fallback would give the user uninhibited instructions for a question we
haven't verified is actually low-risk. If the classifier stub returns "unknown" for a refuse-tier
question (e.g., panel work), the safe fallback would provide full DIY instructions for something
that can cause fire or death.

Why "caution" and not "refuse":
Using the refuse prompt as fallback would block all questions when the classifier is broken —
including genuinely safe questions like "how do I patch drywall?" During development (when the
classifier stub is still returning "unknown"), this makes the system completely unusable.

"Caution" is the right default because it provides genuinely useful information with real safety
framing. A user asking about painting a wall gets instructions with a few unnecessary safety notes —
minor friction. A user asking about gas line work gets instructions with strong stop conditions and
a professional recommendation — not ideal, but far better than providing uninhibited instructions.
The asymmetry of harm favors the cautious default.
```

---

## Implementation Notes

*Fill this in after implementing, before moving to Milestone 3.*

**A "refuse" response that was still too helpful and what you changed to fix it:**

```
[your answer here]
```

**The tier where the LLM's default behavior was closest to what you wanted (and which tier required the most prompt iteration):**

```
[your answer here]
```
