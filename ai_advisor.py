"""
AI Feasibility Advisor (NVIDIA NIM)
==================================
Calls a real LLM hosted on NVIDIA NIM for QUALITATIVE feasibility advice.

SCOPE: This AI does NOT restate cost numbers (the model already computes those).
Its job is reasoning over messy qualitative factors — density, noise rules,
distance, payload, terrain — to advise WHETHER/HOW a route should shift to drones.

Setup:
  1. Free key + credits: https://build.nvidia.com/
  2. Set env var NVIDIA_API_KEY=your_key (or paste into the app sidebar)

NVIDIA NIM exposes an OpenAI-compatible API.

Requires: openai
"""

import os

try:
    from openai import OpenAI
    OPENAI_LIB_AVAILABLE = True
except ImportError:
    OPENAI_LIB_AVAILABLE = False

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "mistralai/mistral-large-2-instruct"


def get_api_key(provided=None):
    return provided or os.environ.get("NVIDIA_API_KEY", "")


def get_feasibility_advice(route_summary, api_key, model=DEFAULT_MODEL):
    if not OPENAI_LIB_AVAILABLE:
        return "⚠️ The 'openai' library isn't installed. Run: pip install openai"

    if not api_key:
        return ("⚠️ No NVIDIA API key set. Add it in the sidebar or set NVIDIA_API_KEY. "
                "Get a free key at https://build.nvidia.com/")

    system_prompt = (
        "You are a last-mile logistics strategy advisor. You are given MODELED "
        "cost estimates for van vs drone delivery on a route. Do NOT simply "
        "restate which is cheaper — the user can already see that. Instead, give "
        "concise qualitative guidance a logistics PM would value: consider "
        "population density, noise/regulatory concerns, package weight limits, "
        "distance profile, weather exposure, and operational readiness. "
        "Recommend whether this route is a good drone candidate, what risks to "
        "watch, and what concrete changes would make a drone shift viable. "
        "Be specific and practical. 4-6 sentences max. Note costs are estimates."
    )

    user_prompt = f"""Route data (modeled estimates):
ZIP: {route_summary.get('zip', 'N/A')}
Road distance (van): {route_summary.get('distance_miles', 'N/A')} miles
Estimated van cost: ${route_summary.get('van_cost', 'N/A')}/delivery
Estimated drone cost: ${route_summary.get('drone_cost', 'N/A')}/delivery
Typical package weight: {route_summary.get('package_lbs', 'N/A')} lbs
Drone payload OK: {route_summary.get('payload_ok', 'N/A')}
Context notes: {route_summary.get('notes', 'none')}

Give qualitative feasibility guidance for shifting this route toward drone delivery."""

    try:
        client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=400,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ AI advice unavailable: {e}"
