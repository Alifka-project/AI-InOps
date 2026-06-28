import os, sys, numpy as np
# The verified engine now lives under backend/core (so the backend deploys
# self-contained). Put backend/ on the path so `import core` resolves.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
from scipy.optimize import linprog
from core import forecasting as fc
from core import transportation as tp
from core import metrics

print("=" * 60)
print("FORECASTING VERIFICATION")
print("=" * 60)

# Hand example: exponential smoothing, alpha=0.5, D=[37,40,41,37,45,50]
demand = [37, 40, 41, 37, 45, 50]
es = fc.exponential_smoothing(demand, alpha=0.5)
# Manual: F1=37; F2=.5*37+.5*37=37; F3=.5*40+.5*37=38.5; F4=.5*41+.5*38.5=39.75
print("Exp smoothing (a=0.5):", [round(x, 3) for x in es])
print("  hand-check F1..F4 -> 37, 37, 38.5, 39.75  | match:",
      np.allclose(es[:4], [37, 37, 38.5, 39.75]))

# Linear trend hand example: y=[37,40,41,37,45,50], x=1..6
lt = fc.linear_trend(demand)
# b = (sum xy - n xbar ybar)/(sum x^2 - n xbar^2)
x = np.arange(1, 7); y = np.array(demand)
b_manual = (np.sum(x*y) - 6*x.mean()*y.mean()) / (np.sum(x**2) - 6*x.mean()**2)
a_manual = y.mean() - b_manual*x.mean()
print(f"\nLinear trend: a={lt.intercept:.4f}, b={lt.slope:.4f}")
print(f"  hand-check : a={a_manual:.4f}, b={b_manual:.4f}  | match:",
      np.isclose(lt.intercept, a_manual) and np.isclose(lt.slope, b_manual))

# Adjusted exp smoothing sanity (alpha=0.5, beta=0.3)
aes = fc.adjusted_exponential_smoothing(demand, alpha=0.5, beta=0.3)
print(f"\nAdjusted ES next-period forecast: {aes.next_forecast:.3f}")
print("  metrics vs simple ES:", metrics.summary(demand, es[:len(demand)]))

print("\n" + "=" * 60)
print("TRANSPORTATION VERIFICATION (vs scipy LP)")
print("=" * 60)

def lp_optimum(cost, supply, demand):
    c, s, d, *_ = tp.balance(cost, supply, demand)
    m, n = c.shape
    cflat = c.flatten()
    # supply equality (<=) and demand equality
    A_eq, b_eq = [], []
    for i in range(m):
        row = np.zeros(m*n); row[i*n:(i+1)*n] = 1; A_eq.append(row); b_eq.append(s[i])
    for j in range(n):
        row = np.zeros(m*n); row[j::n] = 1; A_eq.append(row); b_eq.append(d[j])
    res = linprog(cflat, A_eq=A_eq, b_eq=b_eq, bounds=[(0, None)]*(m*n), method="highs")
    return res.fun

# Balanced classic problem (Taylor grain shipping)
cost = [[6, 8, 10], [7, 11, 11], [4, 5, 12]]
supply = [150, 175, 275]
demand = [200, 100, 300]
lp = lp_optimum(cost, supply, demand)
print(f"\nBalanced problem.  LP optimum = {lp:.1f}")
for init in ["nwc", "least_cost", "vogel"]:
    for opt in ["modi", "stepping_stone"]:
        sol = tp.solve_transport(cost, supply, demand, initial=init, optimize=opt)
        ok = np.isclose(sol.total_cost, lp)
        print(f"  {init:>10} + {opt:<14} -> {sol.total_cost:8.1f}  {'OK' if ok else 'MISMATCH'}")

# Unbalanced problem (supply > demand)
cost2 = [[4, 8, 8], [16, 24, 16], [8, 16, 24]]
supply2 = [76, 82, 77]
demand2 = [72, 102, 41]
lp2 = lp_optimum(cost2, supply2, demand2)
print(f"\nUnbalanced problem (supply>demand).  LP optimum = {lp2:.1f}")
for init in ["nwc", "least_cost", "vogel"]:
    sol = tp.solve_transport(cost2, supply2, demand2, initial=init, optimize="modi")
    ok = np.isclose(sol.total_cost, lp2)
    print(f"  {init:>10} + modi  -> {sol.total_cost:8.1f}  dummy={sol.dummy_added or 'none':<11} {'OK' if ok else 'MISMATCH'}")

# Unbalanced (demand > supply)
cost3 = [[5, 7, 9, 6], [6, 4, 8, 5]]
supply3 = [120, 140]
demand3 = [80, 90, 70, 100]
lp3 = lp_optimum(cost3, supply3, demand3)
print(f"\nUnbalanced problem (demand>supply). LP optimum = {lp3:.1f}")
for init in ["nwc", "least_cost", "vogel"]:
    sol = tp.solve_transport(cost3, supply3, demand3, initial=init, optimize="stepping_stone")
    ok = np.isclose(sol.total_cost, lp3)
    print(f"  {init:>10} + stepping -> {sol.total_cost:8.1f}  dummy={sol.dummy_added or 'none':<11} {'OK' if ok else 'MISMATCH'}")
