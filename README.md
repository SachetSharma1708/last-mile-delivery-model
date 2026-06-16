Last-Mile Delivery Cost Modeler (US)

> Compare van vs drone last-mile delivery economics across delivery ZIP codes, using real route distances, a transparent editable cost model and an AI feasibility advisor.


## What it does
1. Input warehouse ZIP + target delivery ZIPs (+ package weight)
2. Pulls real distances (road for vans, straight line for drones)
3. Estimates per-route costs with a transparent labor weighted model
4. Produces an editable report, change assumptions, delete ZIPs, recalculates
5. Finds the break even: operator-to-drone ratio where drones beat vans
6. AI feasibility advice on qualitative factors

## Key insight
Drone economics aren't about distance or fuel : the dominant lever is how many
drones one operator can supervise (US DOT). This is why Manna (~20:1) is
profitable and Amazon Prime Air struggled.

## Setup
```bash
python -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

### API keys (both free)
1. OpenRouteService (required): https://openrouteservice.org/dev/#/signup
2. NVIDIA NIM (optional, for AI advice): https://build.nvidia.com/

Paste into the app sidebar, or set env vars ORS_API_KEY and NVIDIA_API_KEY.

## Limitations (stated honestly)
- Cost figures are modeled estimates, not real measured costs
- Drone regulations (BVLOS, Part 108) vary by region and aren't modeled
- This is a scenario-planning tool, not a procurement decision system

## License
MIT
