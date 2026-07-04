"""RDKit-backed cheminformatics tools. Everything here is a REAL computation.

Provides: descriptor panel, Tanimoto similarity, PAINS/Brenk structural alerts,
synthetic-accessibility (SA) score, and rule-based analog enumeration used by the
molecular-optimizer agent.
"""
from __future__ import annotations
import os, sys
from functools import lru_cache

from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors, QED, AllChem, DataStructs, RDConfig
from rdkit.Chem.FilterCatalog import FilterCatalog, FilterCatalogParams

RDLogger.DisableLog("rdApp.*")

# --- synthetic accessibility scorer (RDKit contrib) ---
sys.path.append(os.path.join(RDConfig.RDContribDir, "SA_Score"))
try:
    import sascorer  # type: ignore
    def sa_score(mol) -> float:
        return round(float(sascorer.calculateScore(mol)), 2)
except Exception:  # pragma: no cover
    def sa_score(mol) -> float:
        # crude proxy: more rings/heteroatoms -> harder; 1 (easy) .. 10 (hard)
        return round(min(10.0, 1.0 + 0.25 * Descriptors.RingCount(mol)
                         + 0.05 * mol.GetNumHeavyAtoms()), 2)


@lru_cache(maxsize=1)
def _alert_catalog() -> FilterCatalog:
    p = FilterCatalogParams()
    p.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS)
    p.AddCatalog(FilterCatalogParams.FilterCatalogs.BRENK)
    return FilterCatalog(p)


def mol(smiles: str):
    return Chem.MolFromSmiles(smiles)


def canonical(smiles: str) -> str | None:
    m = mol(smiles)
    return Chem.MolToSmiles(m) if m else None


def descriptors(smiles: str) -> dict:
    """Full physicochemical panel used by the ADMET gate and ranking."""
    m = mol(smiles)
    if m is None:
        raise ValueError(f"invalid SMILES: {smiles}")
    return {
        "mw": round(Descriptors.MolWt(m), 1),
        "logp": round(Descriptors.MolLogP(m), 2),
        "hbd": Descriptors.NumHDonors(m),
        "hba": Descriptors.NumHAcceptors(m),
        "tpsa": round(Descriptors.TPSA(m), 1),
        "rotb": Descriptors.NumRotatableBonds(m),
        "qed": round(QED.qed(m), 3),
        "sa_score": sa_score(m),
    }


def structural_alerts(smiles: str) -> list[str]:
    """Return names of matched PAINS/Brenk alerts (empty = clean)."""
    m = mol(smiles)
    if m is None:
        return []
    cat = _alert_catalog()
    return [e.GetDescription() for e in cat.GetMatches(m)]


def _fp(m):
    return AllChem.GetMorganFingerprintAsBitVect(m, radius=2, nBits=2048)


def tanimoto(smiles_a: str, smiles_b: str) -> float:
    a, b = mol(smiles_a), mol(smiles_b)
    if a is None or b is None:
        return 0.0
    return round(DataStructs.TanimotoSimilarity(_fp(a), _fp(b)), 4)


# --- analog enumeration for the optimizer -------------------------------------
# small library of medicinal-chemistry-style single-point edits, as SMARTS rxns.
_RXNS = [
    ("methylation",   "[cH:1]>>[c:1]C"),
    ("fluorination",  "[cH:1]>>[c:1]F"),
    ("hydroxylation", "[cH:1]>>[c:1]O"),
    ("chlorination",  "[cH:1]>>[c:1]Cl"),
    ("amination",     "[cH:1]>>[c:1]N"),
]
_COMPILED = [(name, AllChem.ReactionFromSmarts(smarts)) for name, smarts in _RXNS]


def generate_analogs(smiles: str, n: int, polar_bias: bool = False) -> list[dict]:
    """Enumerate up to `n` valid, unique analogs via single-point aromatic edits.

    `polar_bias=True` (a Critic directive) prioritises polarity-increasing edits
    (hydroxylation/amination) — this is exactly how a re-plan for 'logP too high'
    is realised at the chemistry level.
    """
    parent = mol(smiles)
    if parent is None:
        return []
    order = _COMPILED
    if polar_bias:
        pref = {"hydroxylation", "amination"}
        order = sorted(_COMPILED, key=lambda x: 0 if x[0] in pref else 1)

    seen: set[str] = {Chem.MolToSmiles(parent)}
    out: list[dict] = []
    for name, rxn in order:
        for products in rxn.RunReactants((parent,)):
            if not products:
                continue
            prod = products[0]
            try:
                Chem.SanitizeMol(prod)
            except Exception:
                continue
            csmi = Chem.MolToSmiles(prod)
            if csmi in seen:
                continue
            seen.add(csmi)
            out.append({"smiles": csmi, "edit": name})
            if len(out) >= n:
                return out
    return out
