"""
Approfondissement : impact du cassage de symétrie des couleurs en coloriage.

    python etude_symetries.py [dossier_des_.col] [timeout_s]

Pour chaque instance dont on connaît le nombre chromatique chi (cf. CHI_CONNU), on résout deux problèmes de décision :
    k = chi - 1  (INSATISFIABLE : il faut parcourir tout l'arbre -> c'est là que les symétries coûtent)
    k = chi      (SATISFIABLE   : il faut trouver un coloriage)
pour chaque mode de SYMETRIES et chaque configuration de recherche. Écrit aussi resultats_symetries.csv.

si on connait pas chi et bien on teste de 2 à 7 et si ça ne trouve pas et bien ça s'arrête.

"""
import csv
import os
import sys
from solveur import Solveur
from problemes import lire_col, coloriage, trouver_clique, SYMETRIES

# Valeurs optimales classiques des instances DIMACS (à vérifier sur la page / compléter).
CHI_CONNU = {
    "myciel3": 4, "myciel4": 5, "myciel5": 6, "myciel6": 7,
    "queen5_5": 5, "queen6_6": 7, "queen7_7": 7, "queen8_8": 9,
    "david": 11, "anna": 11, "huck": 11, "jean": 10, "games120": 9,
    "miles250": 8, "miles500": 20,
}
CONFIGS = [("fc", "dom"), ("mac", "dom")]


def main(dossier="instances", timeout=5.0):
    lignes = []
    noms = sorted(f[:-4] for f in os.listdir(dossier) if f.endswith(".col"))
    print(f"{'instance':>10} {'|V|':>4} {'|E|':>5} {'w':>3} {'chi':>3} {'k':>3} {'config':>8} "
          f"{'symétrie':>10} {'résultat':>8} {'noeuds':>9} {'temps(s)':>9}")
    for nom in noms:
        n, aretes = lire_col(os.path.join(dossier, nom + ".col"))
        clique = trouver_clique(n, aretes)
        if nom in CHI_CONNU:
            ks = (CHI_CONNU[nom] - 1, CHI_CONNU[nom])
            res = "UNSAT"
        else:
            ks = range(2, 7)
            res="UNSAT"
        chi = CHI_CONNU.get(nom,"?")
        for k in ks:
            if res=="UNSAT":
                for cons, hv in CONFIGS:
                    for sym in SYMETRIES:
                        s = Solveur(coloriage(n, aretes, k, sym, clique), cons, hv, timeout=timeout)
                        sol = s.resoudre()
                        res = "TIMEOUT" if s.stats.timeout else ("SAT" if sol else "UNSAT")
                        st = s.stats
                        lignes.append([nom, n, len(aretes), len(clique), chi, k, f"{cons}/{hv}", sym,
                                       res, st.noeuds, round(st.temps, 3)])
                        print(f"{nom:>10} {n:>4} {len(aretes):>5} {len(clique):>3} {chi:>3} {k:>3} "
                              f"{cons + '/' + hv:>8} {sym:>10} {res:>8} {st.noeuds:>9} {st.temps:>9.3f}",
                              flush=True)

            elif res=="SAT":
                print("On a trouvé chi.")
            else:
                print("On a dépassé le nombre de tours.")
            print()
    with open("resultats_symetries.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["instance", "V", "E", "taille_clique", "chi", "k", "config", "symetrie",
                    "resultat", "noeuds", "temps_s"])
        w.writerows(lignes)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "instances",
         float(sys.argv[2]) if len(sys.argv) > 2 else 5.0)


