"""
Solveur générique de CSP binaires : backtrack + (rien / forward-checking / MAC)
avec heuristiques de variables / valeurs interchangeables.


Utilisation :
    s = Solveur(csp, consistance="mac", heuristique_var="dom", heuristique_val="static")
    solution = s.resoudre()            # dict {variable: valeur} ou None
    print(s.stats)                     # noeuds, retours arrière, révisions, temps...


Options :
    consistance     : "none" (backtrack pur), "fc" (forward-checking), "mac" (AC3 maintenu)
    ac_racine       : AC3 une fois à la racine (avant toute décision), même en "none"/"fc"
    heuristique_var : "static", "dom", "deg", "dom_deg", "dom_wdeg"  (ou une fonction)
    heuristique_val : "static", "random", "lcv"                      (ou une fonction)
    timeout         : secondes (None = illimité). stats.timeout vaut True si dépassé.
    filtre_valeurs  : f(solveur, x, valeurs) -> valeurs, appliqué après l'heuristique de valeur.
                      Sert à casser des symétries dynamiquement (cf. problemes.py).
                      Par défaut : csp.filtre_valeurs (posé par le modèle, ex. coloriage).


Gestion des domaines : domaines = ensembles courants + "trail" (pile des valeurs
retirées). Au backtrack on remet les valeurs retirées depuis la marque, sans copie
de tous les domaines (cf. cours 3, gestion de la mémoire).
"""


import random
import sys
import time
from collections import deque, defaultdict




class Timeout(Exception):
    pass




class Stats:
    def __init__(self):
        self.noeuds = 0       # affectations tentées (et cohérentes avec le passé)
        self.retours = 0      # retours arrière (un noeud dont tout le sous-arbre échoue)
        self.revisions = 0    # appels à revise / filtrages : mesure le coût de la consistance
        self.solutions = 0
        self.temps = 0.0
        self.timeout = False


    def __repr__(self):
        t = " TIMEOUT" if self.timeout else ""
        return (f"noeuds={self.noeuds} retours={self.retours} "
                f"révisions={self.revisions} solutions={self.solutions} "
                f"temps={self.temps:.3f}s{t}")






# Heuristiques de choix de variable : f(solveur, variables_libres) -> variable
# En cas d'égalité on garde la première dans l'ordre de déclaration.
def var_static(s, libres):
    return libres[0]




def var_dom(s, libres):                 # plus petit domaine courant (first-fail)
    return min(libres, key=lambda x: len(s.dom[x]))




def var_deg(s, libres):                 # la plus contrainte (voisins non instanciés)
    return max(libres, key=s.degre)




def var_dom_deg(s, libres):
    return min(libres, key=lambda x: len(s.dom[x]) / max(1, s.degre(x)))




def var_dom_wdeg(s, libres):            # poids des contraintes qui ont déjà causé un échec
    return min(libres, key=lambda x: len(s.dom[x]) / max(1, s.degre_pondere(x)))




HEURISTIQUES_VAR = {
    "static": var_static, "dom": var_dom, "deg": var_deg,
    "dom_deg": var_dom_deg, "dom_wdeg": var_dom_wdeg,
}




# Heuristiques de choix de valeur : f(solveur, x) -> liste ordonnée de valeurs


def val_static(s, x):
    return sorted(s.dom[x])




def val_random(s, x):
    l = sorted(s.dom[x])
    s.rng.shuffle(l)
    return l




def val_lcv(s, x):
    """Least constraining value : on commence par la valeur qui retire le moins
    de valeurs aux domaines des voisins non instanciés."""
    libres = [y for y in s.csp.voisins[x] if y not in s.inst]


    def cout(v):
        return sum(len(s.dom[y]) - len(s.supports[(x, y)][v] & s.dom[y]) for y in libres)


    return sorted(s.dom[x], key=lambda v: (cout(v), v))




HEURISTIQUES_VAL = {"static": val_static, "random": val_random, "lcv": val_lcv}




class Solveur:
    def __init__(self, csp, consistance="none", heuristique_var="static",
                 heuristique_val="static", ac_racine=False, timeout=None, graine=0,
                 filtre_valeurs=None):
        if consistance not in ("none", "fc", "mac"):
            raise ValueError("consistance doit valoir 'none', 'fc' ou 'mac'")
        self.csp = csp
        self.consistance = consistance
        self.ac_racine = ac_racine
        self.timeout = timeout
        self.filtre_valeurs = (filtre_valeurs if filtre_valeurs is not None
                               else csp.filtre_valeurs)
        self.rng = random.Random(graine)
        self.h_var = (HEURISTIQUES_VAR[heuristique_var]
                      if isinstance(heuristique_var, str) else heuristique_var)
        self.h_val = (HEURISTIQUES_VAL[heuristique_val]
                      if isinstance(heuristique_val, str) else heuristique_val)
        self.supports = csp.compiler_supports()
        self.stats = Stats()
        sys.setrecursionlimit(max(sys.getrecursionlimit(), 10 * len(csp.variables) + 1000))


    def resoudre(self):
        """Première solution trouvée (dict) ou None.
        Si None, regarder stats.timeout pour distinguer 'pas de solution' de 'inconnu'."""
        sols = self._lancer(toutes=False, limite=None)
        return sols[0] if sols else None


    def toutes_les_solutions(self, limite=None):
        return self._lancer(toutes=True, limite=limite)


    def _lancer(self, toutes, limite):
        self.dom = {x: set(d) for x, d in self.csp.domaines.items()}
        self.trail = []
        self.inst = {}
        self.solutions = []
        self.poids = defaultdict(lambda: 1)
        self.stats = Stats()
        self.toutes, self.limite = toutes, limite
        self.n = len(self.csp.variables)
        t0 = time.perf_counter()
        self.deadline = t0 + self.timeout if self.timeout else None
        try:
            ok = True
            if self.consistance == "mac" or self.ac_racine:
                ok = self._ac3(list(self.supports))
            if ok:
                self._rechercher()
        except Timeout:
            self.stats.timeout = True
        self.stats.temps = time.perf_counter() - t0
        self.stats.solutions = len(self.solutions)
        return self.solutions


    def _rechercher(self):
        """Retourne True si la recherche doit s'arrêter (solution trouvée en mode 'première')."""
        if len(self.inst) == self.n:
            self.solutions.append(dict(self.inst))
            return (not self.toutes) or (self.limite is not None
                                         and len(self.solutions) >= self.limite)


        libres = [x for x in self.csp.variables if x not in self.inst]
        x = self.h_var(self, libres)


        valeurs = self.h_val(self, x)
        if self.filtre_valeurs is not None:
            valeurs = self.filtre_valeurs(self, x, valeurs)
        for v in valeurs:
            # Backtrack pur : on vérifie v contre les variables déjà instanciées.
            if self.consistance == "none" and not self._compatible(x, v):
                continue
            self.stats.noeuds += 1
            self._verifier_temps()


            marque = len(self.trail)
            self._affecter(x, v)
            if self.consistance == "fc":
                ok = self._forward_checking(x)
            elif self.consistance == "mac":
                ok = self._ac3([(y, x) for y in self.csp.voisins[x] if y not in self.inst])
            else:
                ok = True


            if ok and self._rechercher():
                return True


            self._restaurer(marque)
            del self.inst[x]


        self.stats.retours += 1
        return False


    def _retirer(self, x, a):
        self.dom[x].discard(a)
        self.trail.append((x, a))


    def _restaurer(self, marque):
        while len(self.trail) > marque:
            x, a = self.trail.pop()
            self.dom[x].add(a)


    def _affecter(self, x, v):
        for b in list(self.dom[x]):
            if b != v:
                self._retirer(x, b)
        self.inst[x] = v


    def _compatible(self, x, v):
        for y in self.csp.voisins[x]:
            if y in self.inst and self.inst[y] not in self.supports[(x, y)][v]:
                return False
        return True


    # Consistance
    def _forward_checking(self, x):
        """x vient d'être fixée à v : on filtre D(y) pour chaque voisin y non instancié.
        Pas de propagation plus loin. False si un domaine devient vide."""
        v = self.inst[x]
        for y in self.csp.voisins[x]:
            if y in self.inst:
                continue
            self.stats.revisions += 1
            sup = self.supports[(x, y)][v]
            for b in list(self.dom[y]):
                if b not in sup:
                    self._retirer(y, b)
            if not self.dom[y]:
                self._echec(x, y)
                return False
        return True


    def _reviser(self, x, y):
        """Retire de D(x) les valeurs sans support dans D(y). True si D(x) a changé."""
        self.stats.revisions += 1
        if self.stats.revisions & 255 == 0:
            self._verifier_temps()
        sup = self.supports[(x, y)]
        dy = self.dom[y]
        modifie = False
        for a in list(self.dom[x]):
            if sup[a].isdisjoint(dy):
                self._retirer(x, a)
                modifie = True
        return modifie


    def _ac3(self, arcs):
        """AC3 (cours 2). arcs : liste de couples (x, y) à réviser.
        False si un domaine devient vide."""
        file = deque(arcs)
        presents = set(file)
        while file:
            x, y = file.popleft()
            presents.discard((x, y))
            if self._reviser(x, y):
                if not self.dom[x]:
                    self._echec(x, y)
                    return False
                for z in self.csp.voisins[x]:
                    if z != y and (z, x) not in presents:
                        file.append((z, x))
                        presents.add((z, x))
        return True


    def _echec(self, x, y):
        """Wipe-out causé par la contrainte {x,y} : on augmente son poids (dom/wdeg)."""
        self.poids[(x, y) if x < y else (y, x)] += 1


    def _verifier_temps(self):
        if self.deadline is not None and time.perf_counter() > self.deadline:
            raise Timeout


    def degre(self, x):
        return sum(1 for y in self.csp.voisins[x] if y not in self.inst)


    def degre_pondere(self, x):
        return sum(self.poids[(x, y) if x < y else (y, x)]
                   for y in self.csp.voisins[x] if y not in self.inst)





