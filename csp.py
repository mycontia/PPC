"""
Modèle d'un CSP binaire en extension (variables entières, domaines finis).
Format:
    variables   : liste d'entiers
    domaines    : {variable: liste de valeurs}
    contraintes : {(x, y): ensemble de tuples (a, b) autorisés}
"""




class CSP:
    def __init__(self):
        self.variables = []     # ordre de déclaration (sert à l'heuristique "static")
        self.domaines = {}      # x -> liste de valeurs
        self.contraintes = {}   # (x, y) -> set de tuples (a, b), toujours symétrisé
        self.voisins = {}       # x -> liste des variables liées à x par une contrainte
        self.filtre_valeurs = None  # optionnel : casse de symétrie fournie par le modèle


    # Construction
    def ajouter_variable(self, x, domaine):
        if x in self.domaines:
            raise ValueError(f"variable {x} déjà déclarée")
        self.variables.append(x)
        self.domaines[x] = list(domaine)
        self.voisins[x] = []


    def ajouter_contrainte(self, x, y, tuples):
        """Contrainte en extension : `tuples` = couples (a, b) autorisés pour (x, y).
        Le sens inverse (y, x) est généré automatiquement.
        Si une contrainte existe déjà sur (x, y), on prend l'intersection."""
        if x == y:
            raise ValueError("contrainte binaire : x et y doivent être différentes")
        if x not in self.domaines or y not in self.domaines:
            raise ValueError("déclarer les variables avant les contraintes")
        tuples = set(tuples)
        self._fusionner(x, y, tuples)
        self._fusionner(y, x, {(b, a) for (a, b) in tuples})


    def ajouter_contrainte_intension(self, x, y, predicat):
        """Contrainte en intension : predicat(a, b) -> bool.
        Exemple : csp.ajouter_contrainte_intension(0, 1, lambda a, b: a != b)"""
        tuples = {(a, b)
                  for a in self.domaines[x]
                  for b in self.domaines[y]
                  if predicat(a, b)}
        self.ajouter_contrainte(x, y, tuples)


    def _fusionner(self, x, y, tuples):
        if (x, y) in self.contraintes:
            self.contraintes[(x, y)] = self.contraintes[(x, y)] & tuples  # nouvel objet
        else:
            self.contraintes[(x, y)] = tuples
            self.voisins[x].append(y)


    # Outils
    def compiler_supports(self):
        """supports[(x, y)][a] = frozenset des valeurs b de D(y) compatibles avec x=a.
        Permet de tester "a a-t-elle un support dans D(y) ?" en O(1) amorti
        (isdisjoint) au lieu de parcourir tous les tuples."""
        supports = {}
        for (x, y), tuples in self.contraintes.items():
            s = {a: set() for a in self.domaines[x]}
            for a, b in tuples:
                if a in s:
                    s[a].add(b)
            supports[(x, y)] = {a: frozenset(bs) for a, bs in s.items()}
        return supports


    def est_solution(self, instanciation):
        """Vérifie indépendamment du solveur qu'une instanciation complète est valide."""
        if set(instanciation) != set(self.variables):
            return False
        for x, a in instanciation.items():
            if a not in self.domaines[x]:
                return False
        for (x, y), tuples in self.contraintes.items():
            if (instanciation[x], instanciation[y]) not in tuples:
                return False
        return True


    def __repr__(self):
        nc = len(self.contraintes) // 2
        return f"CSP({len(self.variables)} variables, {nc} contraintes binaires)"





