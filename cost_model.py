"""
Last-Mile Delivery Cost Model
=============================
Transparent, editable cost model for comparing van vs drone last-mile delivery.

IMPORTANT — read before trusting any number this produces:
Every cost output is a MODELED ESTIMATE, not a real measured cost. No public API
returns a company's actual per-delivery cost — that data is internal. This model
applies published industry benchmarks to real route distances to produce
defensible *estimates*. All defaults are cited and user-editable.

----------------------------------------------------------------------
CITED BENCHMARKS (defaults — all user-editable)
----------------------------------------------------------------------
VAN / GROUND LAST-MILE:
  - US last-mile cost ~$10.10/package; last mile ~53% of shipping cost.
      Source: Capgemini Research Institute last-mile studies.
  - Labor (driver) dominates: ~50-60% of last-mile cost. Fuel ~10-15%.
      Source: industry cost-structure breakdowns (McKinsey, Capgemini).

DRONE DELIVERY (estimates vary widely — that's the core insight):
  - Academic: ~$13.50/drone delivery vs ~$2/vehicle. (UMSL, via AP 2025)
  - Zipline claim: "sub $3" vs $16-20 traditional. (Zipline CEO)
  - Manna (only profitable operator): ~$4/flight, projecting $1 at scale. (DroneXL)
  - US DOT theoretical floor: ~$0.88/delivery; LARGEST variable is drones
    managed per operator. (US DOT ITS)

KEY INSIGHT baked into the model: drone cost is dominated by the
operator-to-drone ratio, NOT distance or energy. This is why Manna
(1 operator : ~20 drones) is profitable and Amazon was not.
----------------------------------------------------------------------
"""

from dataclasses import dataclass, asdict


@dataclass
class VanAssumptions:
    base_cost_per_delivery: float = 10.10
    labor_share: float = 0.55
    fuel_share: float = 0.12
    other_share: float = 0.33
    avg_stops_per_route: int = 80
    fuel_price_per_gallon: float = 3.50
    van_mpg: float = 10.0
    failed_delivery_rate: float = 0.05
    terrain_multiplier: float = 1.0   # USER ASSUMPTION — no standard figure


@dataclass
class DroneAssumptions:
    operator_hourly_wage: float = 25.0
    drones_per_operator: int = 10        # THE key cost lever (DOT finding)
    deliveries_per_drone_per_hour: float = 4.0
    energy_cost_per_delivery: float = 0.10
    maintenance_per_delivery: float = 0.50
    max_payload_lbs: float = 4.0
    drone_unit_cost: float = 30000.0
    drone_lifespan_deliveries: int = 50000
    infrastructure_per_dock: float = 50000.0


def estimate_van_cost(distance_miles, van: VanAssumptions):
    labor = van.base_cost_per_delivery * van.labor_share
    other = van.base_cost_per_delivery * van.other_share

    gallons = (distance_miles * 2) / max(van.van_mpg, 1)
    fuel = (gallons * van.fuel_price_per_gallon) / max(van.avg_stops_per_route, 1)
    fuel = max(fuel, van.base_cost_per_delivery * van.fuel_share * 0.5)

    subtotal = labor + other + fuel
    subtotal *= (1 + van.failed_delivery_rate)
    subtotal *= van.terrain_multiplier

    return {
        "total": round(subtotal, 2),
        "labor": round(labor, 2),
        "fuel": round(fuel, 2),
        "other": round(other, 2),
        "is_estimate": True,
    }


def estimate_drone_cost(distance_miles, drone: DroneAssumptions, package_lbs=2.0):
    feasible = package_lbs <= drone.max_payload_lbs

    deliveries_per_operator_hour = drone.drones_per_operator * drone.deliveries_per_drone_per_hour
    labor_per_delivery = drone.operator_hourly_wage / max(deliveries_per_operator_hour, 0.1)
    hardware_per_delivery = drone.drone_unit_cost / max(drone.drone_lifespan_deliveries, 1)

    total = (labor_per_delivery + drone.energy_cost_per_delivery
             + drone.maintenance_per_delivery + hardware_per_delivery)

    return {
        "total": round(total, 2),
        "labor": round(labor_per_delivery, 2),
        "energy": round(drone.energy_cost_per_delivery, 2),
        "maintenance": round(drone.maintenance_per_delivery, 2),
        "hardware_amortized": round(hardware_per_delivery, 2),
        "feasible": feasible,
        "payload_ok": feasible,
        "is_estimate": True,
    }


def calculate_breakeven(van: VanAssumptions, drone: DroneAssumptions,
                        distance_miles=5.0, package_lbs=2.0):
    van_cost = estimate_van_cost(distance_miles, van)["total"]

    breakeven_ratio = None
    sweep = []
    for ratio in range(1, 51):
        d = DroneAssumptions(**{**asdict(drone), "drones_per_operator": ratio})
        drone_cost = estimate_drone_cost(distance_miles, d, package_lbs)["total"]
        sweep.append({"drones_per_operator": ratio, "drone_cost": drone_cost, "van_cost": van_cost})
        if breakeven_ratio is None and drone_cost <= van_cost:
            breakeven_ratio = ratio

    return {
        "van_cost": van_cost,
        "breakeven_drones_per_operator": breakeven_ratio,
        "sweep": sweep,
        "distance_miles": distance_miles,
    }
