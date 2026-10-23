"""
python tests.py
Idée : toutes les combinaisons (consistance x heuristiques) doivent trouver
EXACTEMENT les mêmes solutions. Si une stratégie diffère, c'est qu'elle est buggée.
"""
import itertools
from csp import CSP
from solveur import Solveur
from problemes import (exemple_pays, reines, coloriage, chromatique, graphe_aleatoire, SYMETRIES)


NB_SOLUTIONS_REINES = {4: 2, 5: 10, 6: 4, 7: 40, 8: 92}


CONFIGS = list(itertools.product(("none", "fc", "mac"),
                                 ("static", "dom", "deg", "dom_deg", "dom_wdeg"),
                                 ("static", "lcv", "random")))




def test_modele():
    csp = CSP()
    csp.ajouter_variable(0, [0, 1])
    csp.ajouter_variable(1, [0, 1])
    csp.ajouter_contrainte(0, 1, {(0, 1)})
    assert csp.contraintes[(1, 0)] == {(1, 0)}, "le sens inverse doit être généré"
    assert csp.est_solution({0: 0, 1: 1})
    assert not csp.est_solution({0: 1, 1: 0})
    assert not csp.est_solution({0: 0})
    print("ok modèle (symétrisation, est_solution)")




def test_exemple_pays():
    csp = exemple_pays()
    for cons, hv, hval in CONFIGS:
        sol = Solveur(csp, cons, hv, hval).resoudre()
        assert sol is not None and csp.est_solution(sol), (cons, hv, hval)
    print("ok exemple 3 pays")




def test_reines_comptage():
    for n, attendu in NB_SOLUTIONS_REINES.items():
        if n > 7 and n != 8:
            continue
        configs = CONFIGS if n <= 7 else [("fc", "dom", "static"), ("mac", "dom_wdeg", "lcv"),
                                          ("none", "static", "static")]
        csp = reines(n)
        for cons, hv, hval in configs:
            s = Solveur(csp, cons, hv, hval)
            sols = s.toutes_les_solutions()
            assert len(sols) == attendu, (n, cons, hv, hval, len(sols), attendu)
            assert all(csp.est_solution(x) for x in sols)
        print(f"ok {n}-reines : {attendu} solutions pour {len(configs)} stratégies")




def test_insatisfiable():
    # triangle en 2 couleurs : pas de solution, détectée par toutes les stratégies
    csp = coloriage(3, [(0, 1), (1, 2), (0, 2)], 2)
    for cons, hv, hval in CONFIGS:
        s = Solveur(csp, cons, hv, hval)
        assert s.resoudre() is None and not s.stats.timeout
    print("ok triangle non 2-colorable")




PETERSEN = (10, [(i, (i + 1) % 5) for i in range(5)] + [(i, i + 5) for i in range(5)]
            + [(5 + i, 5 + (i + 2) % 5) for i in range(5)])




def _sat(n, aretes, k, sym, cons, hv):
    s = Solveur(coloriage(n, aretes, k, sym), cons, hv, timeout=20)
    sol = s.resoudre()
    assert not s.stats.timeout
    if sol is not None:   # la solution doit être valide dans le modèle SANS cassage de symétrie
        assert coloriage(n, aretes, k, "aucune").est_solution(sol), (sym, cons, hv)
    return sol is not None




def test_symetries_coloriage():
    """Le cassage de symétrie ne doit JAMAIS changer la satisfiabilité (ni perdre de solution)."""
    n, aretes = PETERSEN
    assert not _sat(n, aretes, 2, "aucune", "fc", "dom") and _sat(n, aretes, 3, "aucune", "fc", "dom")
    graphes = [PETERSEN] + [graphe_aleatoire(n, p, g) for g in range(25)
                            for n, p in ((9 + g % 6, 0.3 + 0.1 * (g % 4)),)]
    for n, aretes in graphes:
        chi = next(k for k in range(1, n + 1) if _sat(n, aretes, k, "aucune", "fc", "dom"))
        for sym in SYMETRIES:
            for cons in ("none", "fc", "mac"):
                for hv in ("static", "dom", "dom_wdeg"):
                    if chi > 1:
                        assert not _sat(n, aretes, chi - 1, sym, cons, hv), (n, sym, cons, hv)
                    assert _sat(n, aretes, chi, sym, cons, hv), (n, chi, sym, cons, hv)
    print(f"ok  coloriage : {len(graphes)} graphes x {len(SYMETRIES)} symétries x 3 consistances "
          f"x 3 heuristiques, même satisfiabilité partout")




def test_chromatique():
    n, aretes = PETERSEN
    for sym in SYMETRIES:
        r = chromatique(n, aretes, timeout=20, symetrie=sym, consistance="mac", heuristique_var="dom")
        assert r["prouve"] and r["lb"] == 3, (sym, r["lb"], r["ub"])
    print("ok  chromatique(Petersen) = 3")




def test_timeout():
    s = Solveur(reines(40), "none", "static", "static", timeout=0.2)
    s.resoudre()
    assert s.stats.timeout
    print("ok  timeout")




if __name__ == "__main__":
    test_modele()
    test_exemple_pays()
    test_reines_comptage()
    test_insatisfiable()
    test_symetries_coloriage()
    test_chromatique()
    test_timeout()
    print("\nTous les tests passent.")





