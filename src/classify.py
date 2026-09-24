"""Normalise the DC inventory's free-text species names into cultivars."""
import re

# (regex on the combined sci+common string, cultivar key, ornamental?)
RULES = [
    (r"kwanzan",                       "kwanzan",      True),
    (r"snow ?goose",                   "snowgoose",    True),
    (r"okame",                         "okame",        True),
    (r"yedoensis|yodoensis|yoshino|akebono", "yoshino", True),
    (r"subhirtella|higan|pendula|autumnalis", "higan",  True),
    (r"\bmume\b|japanese apricot",     "mume",         True),
    (r"sargent",                       "sargent",      True),
    (r"cerasifera|thunder ?cloud|purple ?leaf", "plum", False),
    (r"virginiana|chokecherry|chekecherry",     "chokecherry", False),
    (r"serotina|black cherry",         "blackcherry",  False),
    (r"\bcerasus\b|tart cherry|montmorency",    "sourcherry",  False),
    (r"\bpersica\b|peach",             "peach",        False),
    (r"armeniaca|apricot",             "apricot",      False),
    (r"salicina|methley|\bplum\b",     "plum",         False),
    (r"\bdulcis\b|almond",             "almond",       False),
    # anything left that is still a Prunus but unnamed
    (r"prunus",                        "unidentified", True),
]

NOT_PRUNUS = re.compile(
    r"pyrus|pistacia|cercis|ulmus|zelkova|morus|juniperus|lagerstroemia|malus|"
    r"syringa|acer|platanus|quercus|picea|pinus|aesculus|cladrastis|chionanthus|"
    r"cornus|no tree|crape myrtle|lilac|redbud|elm|maple|oak|crabapple|"
    r"planetree|spruce|pine|fringetree|yellowwood|horsechestnut|pistache|"
    r"red-cedar|mulberry|pear\b", re.I)

LABEL = {
    "kwanzan":     ("Kwanzan",            "Prunus serrulata 'Kwanzan'"),
    "snowgoose":   ("Snow Goose",         "Prunus 'Snow Goose'"),
    "okame":       ("Okame",              "Prunus 'Okame'"),
    "yoshino":     ("Yoshino",            "Prunus x yedoensis"),
    "higan":       ("Higan",              "Prunus subhirtella"),
    "mume":        ("Japanese apricot",   "Prunus mume"),
    "sargent":     ("Sargent",            "Prunus sargentii"),
    "unidentified":("Cherry, unidentified","Prunus sp."),
    "plum":        ("Purple-leaf plum",   "Prunus cerasifera"),
    "chokecherry": ("Chokecherry",        "Prunus virginiana"),
    "blackcherry": ("Black cherry",       "Prunus serotina"),
    "sourcherry":  ("Sour cherry",        "Prunus cerasus"),
    "peach":       ("Peach",              "Prunus persica"),
    "apricot":     ("Apricot",            "Prunus armeniaca"),
    "almond":      ("Almond",             "Prunus dulcis"),
}

def classify(sci, common):
    """-> (cultivar key, is_ornamental_flowering_cherry) or (None, False)."""
    blob = " ".join(x for x in (sci, common) if x).lower()
    if not blob.strip():
        return "unknown", False
    # a mislabelled row: genus says Prunus, both names say something else
    if NOT_PRUNUS.search(blob) and "prunus" not in blob:
        return None, False
    for pat, key, orn in RULES:
        if re.search(pat, blob):
            return key, orn
    return "unknown", False
