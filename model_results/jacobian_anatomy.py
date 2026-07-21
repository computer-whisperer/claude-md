import sympy as sp
from sympy import Rational as R

x, y, z = sp.symbols('x y z')
u = 1 + x*y
F1 = u**3*z + y**2*u*(4 + 3*x*y)
F2 = y + 3*x*u**2*z + 3*x*y**2*(4 + 3*x*y)
F3 = 2*x - 3*x**2*y - x**3*z

# (1) hand-derived line-congruence equations: the image of each vertical line
#     {(x0,y0)} x C_z should satisfy two planes with coefficients in (x0,y0)
print("R1:", sp.factor(sp.expand(x**3*F1 + u**3*F3)))
print("R2:", sp.factor(sp.expand(x**2*F2 + 3*u**2*F3)))

# (2) fibration hypothesis: source pencil c = x/(1+xy); does F send c-fibers
#     into fibers of the same pencil on the target, for some base map psi?
cands = {
    'F1/(1+F1*F2)': F1/(1 + F1*F2),
    'F3/(1+F3*F2)': F3/(1 + F3*F2),
    'F1/(1+F1*F3)': F1/(1 + F1*F3),
    'F3/(1+F3*F1)': F3/(1 + F3*F1),
    'F2/(1+F2*F1)': F2/(1 + F2*F1),
    'F2/(1+F2*F3)': F2/(1 + F2*F3),
}

def fiber_points(c, ys):
    pts = []
    for yv in ys:
        den = 1 - c*yv
        if den == 0:
            continue
        pts.append((R(c)/den, yv))     # x = c/(1 - c y)  =>  x/(1+xy) = c
    return pts

zs = [R(0), R(1), R(7, 3)]
survivors = set(cands)
for cval in [R(3), R(5, 2), R(-1)]:
    for name in list(survivors):
        vals = set()
        for (xv, yv) in fiber_points(cval, [R(0), R(1), R(-2), R(1, 3)]):
            for zv in zs:
                vals.add(sp.simplify(cands[name].subs({x: xv, y: yv, z: zv})))
        if len(vals) > 1:
            survivors.discard(name)
print("fiber-constant candidates:", survivors or "NONE")

# (3) if one survives, sample the induced base map psi(c) and fit a cubic
for name in survivors:
    expr = cands[name]
    samples = []
    for cval in [R(0), R(1), R(-1), R(3), R(1, 2), R(-3), R(2), R(-2)]:
        pts = fiber_points(cval, [R(0), R(1)])
        xv, yv = pts[0]
        samples.append((cval, sp.simplify(expr.subs({x: xv, y: yv, z: R(0)}))))
    c = sp.symbols('c')
    a3, a2, a1, a0 = sp.symbols('a3 a2 a1 a0')
    psi = a3*c**3 + a2*c**2 + a1*c + a0
    sol = sp.solve([psi.subs(c, s) - v for s, v in samples[:4]], [a3, a2, a1, a0])
    fitted = psi.subs(sol)
    ok = all(sp.simplify(fitted.subs(c, s) - v) == 0 for s, v in samples[4:])
    print(f"{name}: psi(c) = {sp.factor(fitted)}   (holds on holdout samples: {ok})")
    print("   psi at collision base points 0, -2, 2:",
          [fitted.subs(c, v) for v in [0, -2, 2]])
