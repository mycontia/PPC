"""
Problèmes de test, séparés du solveur : chaque fonction CONSTRUIT un CSP,
aucune ne dépend d'une instance particulière.
"""


import random
from csp import CSP
from solveur import Solveur




# Exemple  (3 pays, 2 couleurs)
def exemple_pays():
    # 0 = France, 1 = Espagne, 2 = Belgique ; couleurs 0 = rouge, 1 = bleu
    csp = CSP()
    for x in range(3):
        csp.ajouter_variable(x, [0, 1])
    csp.ajouter_contrainte(0, 1, {(0, 1), (1, 0)})   # le sens (1,0) est généré tout seul
    csp.ajouter_contrainte(0, 2, {(0, 1), (1, 0)})
    return csp




# n-Reines (modèle du cours : variable i = ligne, valeur = colonne)
def reines(n):
    csp = CSP()
    for i in range(n):
        csp.ajouter_variable(i, range(n))
    for i in range(n):
        for j in range(i + 1, n):
            d = j - i
            csp.ajouter_contrainte_intension(i, j, lambda a, b, d=d: a != b and abs(a - b) != d)
    return csp


# Coloriage de graphe
def lire_col(chemin):
    """Lit un fichier DIMACS .col (format de mat.tepper.cmu.edu/COLOR/instances.html).
    Retourne (n, liste d'arêtes avec sommets numérotés à partir de 0)."""
    n, aretes = 0, set()
    with open(chemin) as f:
        for ligne in f:
            t = ligne.split()
            if not t:
                continue
            if t[0] == "p":
                n = int(t[2])
            elif t[0] == "e":
                u, v = int(t[1]) - 1, int(t[2]) - 1
                if u != v:
                    aretes.add((min(u, v), max(u, v)))
    return n, sorted(aretes)




def graphe_aleatoire(n, p, graine=0):
    rng = random.Random(graine)
    return n, [(i, j) for i in range(n) for j in range(i + 1, n) if rng.random() < p]




def _adjacence(n, aretes):
    adj = [set() for _ in range(n)]
    for u, v in aretes:
        adj[u].add(v)
        adj[v].add(u)
    return adj




def trouver_clique(n, aretes, departs=100):
    """Clique gloutonne : depuis chacun des `departs` sommets de plus fort degré,
    on ajoute à chaque pas le candidat qui a le plus de voisins parmi les candidats.
    Sert  -de borne inférieure du nombre chromatique, -à casser la symétrie des couleurs."""
    adj = _adjacence(n, aretes)
    meilleure = []
    for d in sorted(range(n), key=lambda i: -len(adj[i]))[:departs]:
        clique, cand = [d], set(adj[d])
        while cand:
            v = max(cand, key=lambda u: (len(adj[u] & cand), -u))
            clique.append(v)
            cand &= adj[v]
        if len(clique) > len(meilleure):
            meilleure = clique
    return meilleure




def _coloration_gloutonne(n, aretes):
    """Borne supérieure : Welsh-Powell. Retourne (nb_couleurs, {sommet: couleur})."""
    adj = _adjacence(n, aretes)
    couleur = {}
    for x in sorted(range(n), key=lambda i: -len(adj[i])):
        pris = {couleur[y] for y in adj[x] if y in couleur}
        c = 0
        while c in pris:
            c += 1
        couleur[x] = c
    return (max(couleur.values()) + 1 if couleur else 0), couleur




# Modes de cassage de symétrie pour le coloriage (cf. approfondissement) :
#   "aucune"     : rien
#   "sommet"     : couleur 0 imposée au sommet de plus fort degré
#   "clique"     : couleurs 0,1,..,m-1 imposées aux m sommets d'une clique
#   "dynamique"  : à chaque noeud, on n'essaie qu'UNE valeur par classe de couleurs interchangeables
#   "clique+dyn" : les deux précédents
SYMETRIES = ("aucune", "sommet", "clique", "dynamique", "clique+dyn")




def _filtre_couleurs_interchangeables(solveur, x, valeurs):
    """Deux couleurs c, c' sont interchangeables dans l'état courant si elles figurent
    dans exactement les mêmes domaines (les contraintes != sont symétriques en couleurs).
    Alors échanger c et c' dans toute solution donne une solution : essayer c suffit.
    Une couleur déjà utilisée (domaine singleton) ou imposée a une 'signature' unique."""
    dom = solveur.dom
    vus, res = set(), []
    for v in valeurs:
        signature = frozenset(y for y in dom if v in dom[y])
        if signature not in vus:
            vus.add(signature)
            res.append(v)
    return res




def coloriage(n, aretes, k, symetrie="clique+dyn", clique=None):
    """CSP "le graphe (n sommets 0..n-1) est-il k-colorable ?"  (variable = sommet,
    valeur = couleur dans [0,k-1], contrainte x != y pour chaque arête).
    `symetrie` : voir SYMETRIES. `clique` : clique déjà calculée (évite de la recalculer)."""
    if symetrie not in SYMETRIES:
        raise ValueError(f"symetrie doit être dans {SYMETRIES}")
    fixes = {}   # sommet -> couleur imposée
    if symetrie == "sommet" and n:
        deg = [0] * n
        for u, v in aretes:
            deg[u] += 1
            deg[v] += 1
        fixes[max(range(n), key=lambda i: deg[i])] = 0
    elif symetrie in ("clique", "clique+dyn"):
        if clique is None:
            clique = trouver_clique(n, aretes)
        for i, x in enumerate(clique):
            fixes[x] = i            # si i >= k : domaine vide => instance infaisable
    csp = CSP()
    for x in range(n):
        if x in fixes:
            csp.ajouter_variable(x, [fixes[x]] if fixes[x] < k else [])
        else:
            csp.ajouter_variable(x, range(k))
    diff = {(a, b) for a in range(k) for b in range(k) if a != b}   # partagé par toutes les arêtes
    for u, v in aretes:
        csp.ajouter_contrainte(u, v, diff)
    if symetrie in ("dynamique", "clique+dyn"):
        csp.filtre_valeurs = _filtre_couleurs_interchangeables
    return csp




def chromatique(n, aretes, timeout=10, symetrie="clique+dyn", **options_solveur):
    """Optimisation par une suite de problèmes de décision, par dichotomie (cours 1).
    Retourne un dict : lb, ub, prouve (lb == ub), solution (coloriage avec ub couleurs),
    appels (liste des (k, résultat, stats)).  Chaque décision a son propre timeout."""
    ub, meilleure = _coloration_gloutonne(n, aretes)
    clique = trouver_clique(n, aretes)
    lb = max(1, len(clique)) if n else 0
    appels = []
    while lb < ub:
        k = (lb + ub) // 2
        s = Solveur(coloriage(n, aretes, k, symetrie, clique), timeout=timeout, **options_solveur)
        sol = s.resoudre()
        if sol is not None:
            meilleure = sol
            ub = len(set(sol.values()))
            appels.append((k, "SAT", s.stats))
        elif s.stats.timeout:
            appels.append((k, "TIMEOUT", s.stats))
            break
        else:
            lb = k + 1
            appels.append((k, "UNSAT", s.stats))
    return {"lb": lb, "ub": ub, "prouve": lb == ub, "solution": meilleure, "appels": appels}





