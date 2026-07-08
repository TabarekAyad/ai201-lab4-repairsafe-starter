import re

from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL, VALID_TIERS

_client = Groq(api_key=GROQ_API_KEY)


def classify_safety_tier(question: str) -> dict:
    """
    Classify a home repair question into one of three safety tiers.

    TODO — Milestone 1:

    Before writing any code, complete specs/classifier-spec.md. The blank fields
    there are the decisions that drive this implementation — prompt design, tier
    definitions, output format, and edge case handling.

    Your implementation should:
      1. Build a prompt using your tier definitions that asks the LLM to classify
         the question and explain its reasoning
      2. Send a single chat completion request (no tools, no history)
      3. Parse the tier and reason out of the raw response text
      4. Validate the tier against VALID_TIERS; fall back to "caution" if the
         response can't be parsed or the tier isn't recognized
      5. Return {"tier": ..., "reason": ...}

    Returns a dict with:
      - "tier"   : str — one of "safe", "caution", "refuse"
      - "reason" : str — a brief explanation of why this tier was assigned

    The three tiers:
      - "safe"    : routine, low-risk repairs most homeowners can handle safely
      - "caution" : doable with care, but mistakes have real cost or mild risk
      - "refuse"  : high-risk repairs that require a licensed professional —
                    mistakes can cause fire, flooding, injury, or structural damage
    """
    system_message = """You are a home repair safety classifier. Your only job is to assign the user's question to one of three safety tiers and explain why in one sentence.

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
Reason: [one sentence explaining the tier assignment]"""

    user_message = f"Classify this home repair question:\n\n{question}"

    response = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
    )

    raw = response.choices[0].message.content or ""

    tier_match = re.search(r"(?i)^Tier:\s*(.+)", raw, re.MULTILINE)
    reason_match = re.search(r"(?i)^Reason:\s*(.+)", raw, re.MULTILINE)

    if not tier_match:
        return {
            "tier": "caution",
            "reason": "Classification could not be parsed; defaulting to caution as a conservative fallback.",
        }

    # Strip surrounding punctuation (quotes, colons, asterisks) then lowercase.
    # Handles: "Refuse", 'caution', refuse:, **safe**, etc.
    raw_tier = re.sub(r"^[^a-zA-Z]+|[^a-zA-Z]+$", "", tier_match.group(1).strip()).lower()

    if raw_tier not in VALID_TIERS:
        return {
            "tier": "caution",
            "reason": "Unrecognized tier value returned; defaulting to caution as a conservative fallback.",
        }

    reason = reason_match.group(1).strip() if reason_match else "No reason provided."

    return {"tier": raw_tier, "reason": reason}
