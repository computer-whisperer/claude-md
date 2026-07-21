import sympy as sp
from sympy import Rational as R

x, y, z = sp.symbols('x y z')
u = 1 + x*y; w = x*y
F1 = u**3*z + y**2*u*(4+3*w)
F2 = y + 3*x*u**2*z + 3*x*y**2*(4+3*w)
F3 = 2*x - 3*x**2*y - x**3*z

# claimed core decomposition
p = u**2*z + y**2*(4 + 3*w)
q = 2 - 3*w - x**2*z
print("F = (u*p, y+3x*p, x*q):",
      sp.expand(F1 - u*p) == 0, sp.expand(F2 - (y + 3*x*p)) == 0, sp.expand(F3 - x*q) == 0)
print("syzygy x^2*p + u^2*q - (1+u) =", sp.expand(x**2*p + u**2*q - (1 + u)))

# claimed Z/2 equivariance: sigma(x,y,z)=(-x,-y,z) intertwines with sigma'(X,Y,Z)=(X,-Y,-Z)
s = {x: -x, y: -y}
print("equivariance:", sp.expand(F1.subs(s) - F1) == 0,
      sp.expand(F2.subs(s) + F2) == 0, sp.expand(F3.subs(s) + F3) == 0)

# geometric degree: eliminate z via Z = x*q, reduce fiber to plane curves in (x, w)
wv = sp.symbols('wv'); U = 1 + wv
def fiber_eqs(Xv, Yv, Zv):
    Pi = U**2*((2 - 3*wv)*x - Zv) + x*wv**2*(4 + 3*wv)   # = x^3 * p
    E1 = sp.expand(Xv*x**3 - U*Pi)                        # X = u p
    E2 = sp.expand(x*(x*Yv - wv) - 3*Pi)                  # Y = y + 3x p
    return E1, E2

# sanity: known collision point P2=(x,w)=(1,-3/2) over target (-1/4,0,0)
E1, E2 = fiber_eqs(R(-1,4), 0, 0)
print("collision sanity:", E1.subs({x:1, wv:R(-3,2)}) == 0, E2.subs({x:1, wv:R(-3,2)}) == 0)

# generic target: count solutions with x != 0
E1, E2 = fiber_eqs(R(5,7), R(-3,4), R(9,5))
res = sp.factor(sp.resultant(E1, E2, wv))
print("resultant over generic target, factored:")
print(" ", res)
