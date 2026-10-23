"""
python benchmark.py
Compare les stratégies (consistance x heuristique de variable) sur :
  - n-Reines (première solution)
  - coloriage : nombre chromatique d'instances DIMACS (.col) :
python benchmark.py dossier_des_col myciel3 myciel4 queen5_5 ... [--symetrie=aucune] [--sans-reines]
"""
import os
import sys
from solveur import Solveur
from problemes import reines, lire_col, chromatique


CONFIGS = [
    ("none", "static"),
    ("fc",   "static"),
    ("fc",   "dom"),
    ("mac",  "static"),
    ("mac",  "dom"),
    ("mac",  "dom_wdeg"),
]
TIMEOUT = 10




def bench_reines(tailles):
    print(f"\n n-Reines, première solution (timeout {TIMEOUT}s)")
    print(f"{'n':>4} {'consistance':>11} {'var':>9} {'noeuds':>9} {'retours':>9} "
          f"{'révisions':>10} {'temps(s)':>9}")
    for n in tailles:
        csp = reines(n)
        for cons, hv in CONFIGS:
            s = Solveur(csp, cons, hv, "static", timeout=TIMEOUT)
            sol = s.resoudre()
            st = s.stats
            etat = "TO" if st.timeout else f"{st.temps:9.3f}"
            ok = "" if (st.timeout or csp.est_solution(sol)) else "  !!! INVALIDE"
            print(f"{n:>4} {cons:>11} {hv:>9} {st.noeuds:>9} {st.retours:>9} "
                  f"{st.revisions:>10} {etat:>9}{ok}")
        print()




def bench_coloriage(dossier, noms, symetrie="clique+dyn"):
    """noms : noms des fichiers .col (sans extension) présents dans `dossier`."""
    print(f"\nColoriage : nombre chromatique par dichotomie "
          f"(timeout {TIMEOUT}s / décision, symétrie={symetrie})")
    print(f"{'instance':>12} {'|V|':>4} {'|E|':>5} {'consistance':>11} {'var':>9} "
          f"{'lb':>3} {'ub':>3} {'prouvé':>7} {'noeuds':>9} {'temps(s)':>9}")
    for nom in noms:
        n, aretes = lire_col(os.path.join(dossier, nom + ".col"))
        for cons, hv in [("fc", "dom"), ("mac", "dom"), ("mac", "dom_wdeg")]:
            r = chromatique(n, aretes, timeout=TIMEOUT, symetrie=symetrie,
                            consistance=cons, heuristique_var=hv)
            noeuds = sum(st.noeuds for _, _, st in r["appels"])
            temps = sum(st.temps for _, _, st in r["appels"])
            print(f"{nom:>12} {n:>4} {len(aretes):>5} {cons:>11} {hv:>9} "
                  f"{r['lb']:>3} {r['ub']:>3} {str(r['prouve']):>7} {noeuds:>9} {temps:>9.3f}")
        print()




if __name__ == "__main__":
    # Options : --symetrie=aucune/sommet/clique/dynamique/clique+dyn   (defaut : clique+dyn)
    #           --sans-reines   (ne lance pas les n-Reines)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sym = "clique+dyn"
    for a in sys.argv[1:]:
        if a.startswith("--symetrie="):
            sym = a.split("=", 1)[1]
        elif a.startswith("--timeout="):
            timeout = float(a.split("=", 1)[1])
    if "--sans-reines" not in sys.argv:
        bench_reines([8, 12, 16, 20])
    if len(args) >= 2:
        bench_coloriage(args[0], args[1:], sym)



