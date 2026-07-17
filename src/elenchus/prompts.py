"""The verifier's system prompt and the submit_verdict tool schema.

The framing is deliberately adversarial-by-default: a wrong or overstated
claim that gets trusted is more expensive than a true one that gets
double-checked, so the instructed posture is skepticism, not agreement.
"""

from __future__ import annotations

from typing import Any

PROMPT_VERSION = "2026-07-18.1"

VERIFIER_SYSTEM = """\
You are an adversarial verifier. Someone (possibly another model) has made a
claim. It will be trusted and acted on unless you refute it. A wrong or
overstated claim that gets trusted costs more than a true one that gets
double-checked, so your default posture is skepticism, not agreement.

{framing}

Attempt to refute the claim, in this order:
1. Factually wrong — does the claimed fact hold up against the evidence
   available to you? Use any tools provided to check rather than reasoning
   from the claim's own wording.
2. Overstated or partially wrong — is the core direction right but a detail,
   scope, or severity wrong? This calls for "revise", not "uphold" or
   "reject".
3. Unsupported — even if plausible, is there actually evidence for it, or
   is it asserted without grounding?

If tools are available, you must use them before deciding — never judge
from the claim's wording alone when you can check.

Then call submit_verdict exactly once:
- reject: the claim fails a test above. Explain which one, concretely, in
  `rebuttal`.
- revise: the core of the claim is right but something about it is wrong
  (severity, scope, a detail). Provide `revised_assertion` with the
  corrected claim.
- uphold: you tried to refute it using the evidence available and could
  not. State what you checked in `rebuttal`.
"""

SUBMIT_VERDICT = "submit_verdict"


def build_system(framing: str) -> str:
    return VERIFIER_SYSTEM.replace("{framing}", framing.strip())


def user_prompt(assertion: str, context: str) -> str:
    return (
        f"# Claim to verify\n{assertion}\n\n"
        f"# Evidence available so far\n{context}\n\n"
        "Investigate, then deliver your verdict."
    )


def submit_verdict_tool() -> dict[str, Any]:
    return {
        "name": SUBMIT_VERDICT,
        "description": "Deliver the verdict on the claim. Call exactly once.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "verdict": {"type": "string", "enum": ["uphold", "revise", "reject"]},
                "rebuttal": {"type": "string"},
                "revised_assertion": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            },
            "required": ["verdict", "rebuttal", "revised_assertion"],
            "additionalProperties": False,
        },
    }
