import os
import sys
# The verified engine now lives under backend/core. Put backend/ on the path.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
import numpy as np
from core import data_generator as dg
from core import forecasting as fc
from core import supplier as sup
from core import warehouse as wh
from core import transportation as tp
from core import metrics

data = dg.build_all()
demand = data["demand"]["returned_units"].to_numpy()

print("DIGITAL TWIN — END-TO-END PIPELINE (appliance/battery recycling)")
print("=" * 64)

# 1. DEMAND FORECASTING -------------------------------------------------
train, test = demand[:-6], demand[-6:]
aes = fc.adjusted_exponential_smoothing(train, alpha=0.4, beta=0.3)
lt = fc.linear_trend(train)
seas = fc.seasonal_adjustment(demand, season_length=12)
print("\n[1] DEMAND FORECASTING")
print(f"  Adjusted ES next-month forecast : {aes.next_forecast:,.0f} units")
print(f"  Linear-trend next-month forecast: {lt.predict(1)[0]:,.0f} units")
print(f"  Seasonal factors (Jan..Dec)     : "
      f"{[round(s,2) for s in seas.seasonal_factors]}")
print(f"  In-sample accuracy (Adj ES)     : "
      f"{metrics.summary(train, aes.adjusted[:len(train)])}")
fc_demand = aes.next_forecast

# 2. SUPPLIER FORECASTING ----------------------------------------------
avail = sup.forecast_supplier_availability(data["supplier_history"], data["centers"])
print("\n[2] SUPPLIER AVAILABILITY FORECAST")
print(avail[["center", "forecast_next_t", "available_t",
             "capacity_utilization"]].to_string(index=False))

# 3. TRANSPORTATION OPTIMIZATION ---------------------------------------
supply = sup.supply_vector(avail)
hub_demand = data["hubs"]["processing_demand_t"].to_numpy(dtype=float)
cost = data["transport_costs"].to_numpy(dtype=float)
print("\n[3] TRANSPORTATION OPTIMIZATION")
print(f"  total supply={supply.sum():.0f} t, total demand={hub_demand.sum():.0f} t "
      f"-> {'balanced' if abs(supply.sum()-hub_demand.sum())<1e-6 else 'UNBALANCED'}")
results = {}
for init in ["nwc", "least_cost", "vogel"]:
    sol = tp.solve_transport(cost, supply, hub_demand, initial=init, optimize="modi")
    results[init] = sol.total_cost
    print(f"  {init:>10} + MODI -> total cost = {sol.total_cost:,.0f} "
          f"(dummy {sol.dummy_added or 'none'})")
print(f"  All methods agree on optimum: "
      f"{len(set(round(v) for v in results.values())) == 1}")

# 4. WAREHOUSE POLICY --------------------------------------------------
demand_std = float(np.std(demand))
avg_lead = float(data["centers"]["lead_time_days"].mean())
policies = wh.hub_policies(data["hubs"], fc_demand, demand_std, avg_lead)
print("\n[4] WAREHOUSE INVENTORY POLICY")
print(policies.to_string(index=False))

# 5. RECOVERED MATERIAL VALUE ------------------------------------------
mat = data["materials"]
processed = min(supply.sum(), hub_demand.sum())
mat = mat.assign(recovered_t=(mat["mass_share"] * processed).round(1),
                 value_usd=(mat["mass_share"] * processed * mat["value_per_t_usd"]).round(0))
print("\n[5] RECOVERED-MATERIAL VALUE (per cycle)")
print(mat[["material", "recovered_t", "value_usd"]].to_string(index=False))
print(f"  Total recovered value: ${mat['value_usd'].sum():,.0f}")
print("\nPipeline OK ✓")
