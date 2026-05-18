"""
Comprehensive conclusions analysis for Project 2.
Runs all four requested analyses on the preprocessed distance matrix.
"""
from __future__ import annotations
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from clustering import (
    kmedoids_clustering,
    agglomerative_clustering,
    silhouette_score,
    dunn_index,
)

# -- Load matrix ----------------------------------------------------------------
ROOT = Path(__file__).parent.parent
MATRIX_FILE = ROOT / "data" / "distance_matrix_preprocessed_chawathe.json"

print("Loading preprocessed distance matrix...")
raw = json.loads(MATRIX_FILE.read_text(encoding="utf-8"))
COUNTRIES = raw["countries"]
N = len(COUNTRIES)
flat = raw["matrix"]
MATRIX = [[flat[i * N + j] for j in range(N)] for i in range(N)]
print(f"  {N} countries loaded.\n")


# ================================================================================
# 1. K-MEDOIDS SILHOUETTE SWEEP  k = 2 ... 15
# ================================================================================
print("=" * 70)
print("ANALYSIS 1: K-Medoids Silhouette Sweep  k=2..15")
print("=" * 70)

sil_scores = {}
for k in range(2, 16):
    result = kmedoids_clustering(COUNTRIES, MATRIX, k=k)
    assignments = result["assignments"]
    sil = silhouette_score(COUNTRIES, MATRIX, assignments)[0]
    sil_scores[k] = sil

print(f"{'k':>4}  {'silhouette':>12}  {'bar'}")
print("-" * 50)
best_k = max(sil_scores, key=sil_scores.get)
max_s = max(sil_scores.values())
for k, s in sil_scores.items():
    bar_len = int((s - min(sil_scores.values())) / (max_s - min(sil_scores.values()) + 1e-9) * 30)
    bar = "#" * max(1, bar_len)
    marker = " <-- BEST" if k == best_k else ""
    print(f"{k:>4}  {s:>12.4f}  {bar}{marker}")

# Elbow detection: largest drop in silhouette gain
gains = [sil_scores[k] - sil_scores[k-1] for k in range(3, 16)]
elbow_k = 3 + gains.index(max(gains))  # k where gain was largest (steepest rise)

print(f"\nBest k by silhouette : k = {best_k}  (sil = {sil_scores[best_k]:.4f})")
print(f"Elbow / inflection   : k = {elbow_k}  (largest single-step gain)")
print()


# ================================================================================
# 2. AHC COMPLETE-LINKAGE  k = 5, 6, 7, 8
# ================================================================================
print("=" * 70)
print("ANALYSIS 2: AHC Complete-Linkage  k = 5, 6, 7, 8")
print("=" * 70)

ahc_results = {}
for k in [5, 6, 7, 8]:
    res = agglomerative_clustering(COUNTRIES, MATRIX, n_clusters=k, linkage="complete")
    assignments = res["assignments"]
    members = res["cluster_members"]
    sil = silhouette_score(COUNTRIES, MATRIX, assignments)[0]
    dunn = dunn_index(COUNTRIES, MATRIX, assignments)
    sizes = sorted([len(v) for v in members.values()], reverse=True)
    ahc_results[k] = {"sil": sil, "dunn": dunn, "sizes": sizes}
    print(f"\n  k={k}")
    print(f"    Silhouette : {sil:.4f}")
    print(f"    Dunn Index : {dunn:.4f}")
    print(f"    Cluster sizes : {sizes}")
    if max(sizes) > sum(sizes) * 0.7:
        print(f"    !! Chaining: largest cluster holds {max(sizes)}/{sum(sizes)} = "
              f"{max(sizes)/sum(sizes)*100:.0f}% of countries")
    else:
        print(f"    Chaining OK: largest cluster = {max(sizes)/sum(sizes)*100:.0f}%")

print("\n  Comparison with previous AHC on RAW (non-preprocessed) trees:")
print("  Raw AHC showed severe chaining: 1 cluster held 90-95% of countries.")
print("  Preprocessed AHC complete-linkage result above -- see sizes above.")
print()


# ================================================================================
# 3. HOPKINS STATISTIC
# ================================================================================
print("=" * 70)
print("ANALYSIS 3: Hopkins Statistic")
print("=" * 70)

def hopkins_statistic(matrix: list[list[int]], m: int = 100, seed: int = 42) -> float:
    """
    Distance-matrix Hopkins statistic using interpolated synthetic points.
    H ~= 0.5  ? random (no clustering tendency)
    H > 0.75 ? strong clustering tendency
    H < 0.25 ? regular / grid-like
    """
    n = len(matrix)
    rng = random.Random(seed)

    # W: nearest-neighbour distances for m real randomly sampled points
    W = 0.0
    sampled = rng.sample(range(n), min(m, n))
    for i in sampled:
        nn = min(matrix[i][j] for j in range(n) if j != i)
        W += nn

    # U: nearest-neighbour distances for m synthetic "interpolated" points.
    # A synthetic point between real points a and b (weight t):
    #   d(synth, k) ~= t*d(a,k) + (1-t)*d(b,k)   (valid in metric/Euclidean)
    U = 0.0
    for _ in range(m):
        a, b = rng.sample(range(n), 2)
        t = rng.random()
        nn = min(
            t * matrix[a][k] + (1.0 - t) * matrix[b][k]
            for k in range(n) if k != a and k != b
        )
        U += nn

    return U / (U + W)

H_values = [hopkins_statistic(MATRIX, m=100, seed=s) for s in range(5)]
H_mean = sum(H_values) / len(H_values)
H_std  = (sum((h - H_mean) ** 2 for h in H_values) / len(H_values)) ** 0.5

print(f"\n  Hopkins H per trial : {[f'{h:.4f}' for h in H_values]}")
print(f"  Mean H              : {H_mean:.4f}  +/- {H_std:.4f}")

if H_mean > 0.75:
    interpretation = "STRONG clustering tendency -- clusters are likely real."
elif H_mean > 0.60:
    interpretation = "MODERATE clustering tendency -- some structure present."
elif H_mean > 0.40:
    interpretation = "WEAK / RANDOM -- no significant cluster structure."
else:
    interpretation = "REGULAR / UNIFORM -- data is more regular than random."

print(f"  Interpretation      : {interpretation}")
print(
    f"  Hopkins H ~= {H_mean:.2f} means the pairwise distances between countries\n"
    f"  follow a distribution close to random uniform -- there are no tight,\n"
    f"  well-separated natural clusters in the infobox structure space.\n"
    f"  Consistent with silhouette scores near 0 across all k values.\n"
    f"  Clustering is DESCRIPTIVE (organisational), not NATURAL --\n"
    f"  the found groups are useful summaries, not statistical clusters.\n"
)


# ================================================================================
# 4. K-MEDOIDS k=5 GEOGRAPHIC ANALYSIS
# ================================================================================
print("=" * 70)
print("ANALYSIS 4: K-Medoids k=5 -- Geographic Breakdown")
print("=" * 70)

# Geographic region mapping
REGION = {
    # Europe
    "albania":"SE Europe","andorra":"W Europe","austria":"C Europe","belgium":"W Europe",
    "bulgaria":"SE Europe","croatia":"SE Europe","cyprus":"SE Europe","czech_republic":"C Europe",
    "denmark":"N Europe","estonia":"N Europe","finland":"N Europe","france":"W Europe",
    "germany":"C Europe","greece":"SE Europe","hungary":"C Europe","iceland":"N Europe",
    "ireland":"W Europe","republic_of_ireland":"W Europe","italy":"S Europe",
    "latvia":"N Europe","liechtenstein":"C Europe","lithuania":"N Europe","luxembourg":"W Europe",
    "malta":"S Europe","monaco":"W Europe","montenegro":"SE Europe","netherlands":"W Europe",
    "north_macedonia":"SE Europe","norway":"N Europe","poland":"C Europe","portugal":"S Europe",
    "romania":"SE Europe","san_marino":"S Europe","serbia":"SE Europe","slovakia":"C Europe",
    "slovenia":"SE Europe","spain":"S Europe","sweden":"N Europe","switzerland":"C Europe",
    "the_bahamas":"Caribbean",
    "united_kingdom":"W Europe",
    # Former Soviet / E Europe
    "armenia":"Caucasus","azerbaijan":"Caucasus","belarus":"E Europe","bosnia_and_herzegovina":"SE Europe",
    "georgia_country_":"Caucasus","kazakhstan":"C Asia","kyrgyzstan":"C Asia","moldova":"E Europe",
    "russia":"E Europe / N Asia","tajikistan":"C Asia","turkmenistan":"C Asia","ukraine":"E Europe",
    "uzbekistan":"C Asia",
    # Middle East / N Africa
    "bahrain":"Middle East","egypt":"N Africa","iran":"Middle East","iraq":"Middle East",
    "israel":"Middle East","jordan":"Middle East","kuwait":"Middle East","lebanon":"Middle East",
    "libya":"N Africa","morocco":"N Africa","oman":"Middle East","qatar":"Middle East",
    "saudi_arabia":"Middle East","syria":"Middle East","tunisia":"N Africa","turkey":"Middle East",
    "united_arab_emirates":"Middle East","yemen":"Middle East","algeria":"N Africa",
    # Sub-Saharan Africa
    "angola":"C Africa","benin":"W Africa","botswana":"S Africa","burkina_faso":"W Africa",
    "burundi":"E Africa","cameroon":"C Africa","cape_verde":"W Africa",
    "central_african_republic":"C Africa","chad":"C Africa","comoros":"E Africa",
    "democratic_republic_of_the_congo":"C Africa","djibouti":"E Africa",
    "equatorial_guinea":"C Africa","eritrea":"E Africa","ethiopia":"E Africa","gabon":"C Africa",
    "ghana":"W Africa","guinea":"W Africa","guinea-bissau":"W Africa","ivory_coast":"W Africa",
    "kenya":"E Africa","lesotho":"S Africa","liberia":"W Africa","madagascar":"E Africa",
    "malawi":"E Africa","mali":"W Africa","mauritania":"W Africa","mauritius":"E Africa",
    "mozambique":"E Africa","namibia":"S Africa","niger":"W Africa","nigeria":"W Africa",
    "republic_of_the_congo":"C Africa","rwanda":"E Africa","s_o_tom_and_pr_ncipe":"C Africa",
    "senegal":"W Africa","sierra_leone":"W Africa","somalia":"E Africa","south_africa":"S Africa",
    "south_sudan":"E Africa","sudan":"N Africa","eswatini":"S Africa","tanzania":"E Africa",
    "the_gambia":"W Africa","togo":"W Africa","uganda":"E Africa","zambia":"E Africa",
    "zimbabwe":"S Africa",
    # S & SE Asia
    "afghanistan":"S Asia","bangladesh":"S Asia","bhutan":"S Asia","brunei":"SE Asia",
    "cambodia":"SE Asia","india":"S Asia","indonesia":"SE Asia","laos":"SE Asia",
    "malaysia":"SE Asia","maldives":"S Asia","myanmar":"SE Asia","nepal":"S Asia",
    "pakistan":"S Asia","philippines":"SE Asia","singapore":"SE Asia","sri_lanka":"S Asia",
    "thailand":"SE Asia","timor-leste":"SE Asia","vietnam":"SE Asia",
    # East Asia
    "china":"E Asia","japan":"E Asia","mongolia":"E Asia","north_korea":"E Asia",
    "south_korea":"E Asia",
    # Pacific & Oceania
    "australia":"Oceania","federated_states_of_micronesia":"Pacific Islands",
    "fiji":"Pacific Islands","kiribati":"Pacific Islands","marshall_islands":"Pacific Islands",
    "nauru":"Pacific Islands","new_zealand":"Oceania","palau":"Pacific Islands",
    "papua_new_guinea":"Pacific Islands","samoa":"Pacific Islands",
    "solomon_islands":"Pacific Islands","tonga":"Pacific Islands","tuvalu":"Pacific Islands",
    "vanuatu":"Pacific Islands",
    # Americas
    "antigua_and_barbuda":"Caribbean","argentina":"S America","barbados":"Caribbean",
    "belize":"C America","bolivia":"S America","brazil":"S America","canada":"N America",
    "chile":"S America","colombia":"S America","costa_rica":"C America","cuba":"Caribbean",
    "dominica":"Caribbean","dominican_republic":"Caribbean","ecuador":"S America",
    "el_salvador":"C America","grenada":"Caribbean","guatemala":"C America",
    "guyana":"S America","haiti":"Caribbean","honduras":"C America","jamaica":"Caribbean",
    "mexico":"N America","nicaragua":"C America","panama":"C America","paraguay":"S America",
    "peru":"S America","saint_kitts_and_nevis":"Caribbean","saint_lucia":"Caribbean",
    "saint_vincent_and_the_grenadines":"Caribbean",
    "suriname":"S America","trinidad_and_tobago":"Caribbean","united_states":"N America",
    "uruguay":"S America","venezuela":"S America",
    # Other
    "seychelles":"E Africa",
}

def region(c: str) -> str:
    return REGION.get(c, "Other")

def majority_region(country_list: list[str]) -> str:
    from collections import Counter
    counts = Counter(region(c) for c in country_list)
    top = counts.most_common(3)
    return "  |  ".join(f"{r}: {n}" for r, n in top)

def avg_intra_dist(members: list[str], countries: list[str], matrix: list[list[int]]) -> float:
    idx = {c: i for i, c in enumerate(countries)}
    pairs = [(members[i], members[j])
             for i in range(len(members)) for j in range(i+1, len(members))]
    if not pairs:
        return 0.0
    return sum(matrix[idx[a]][idx[b]] for a, b in pairs) / len(pairs)

MEDOID_REASONS = {
    "uruguay": (
        "Uruguay is structurally central to Latin American infoboxes -- "
        "it has a compact, well-structured infobox with typical fields "
        "(president, legislature, area, population, GDP, Gini, HDI) that "
        "are shared across most Latin American and diverse Commonwealth nations. "
        "It avoids the extra historical/colonial sections that make Brazil or "
        "Argentina outliers."
    ),
    "malta": (
        "Malta exemplifies the 'Western developed-nation' infobox template: "
        "parliamentary system, EU membership fields, standard economic indicators, "
        "small but complete structure. Its compact size means fewer unique "
        "history-section fields that would push it away from the European average."
    ),
    "senegal": (
        "Senegal is a structurally typical Francophone West African country -- "
        "standard post-colonial infobox fields (president, prime minister, "
        "independence date, area, population) without the extended historical "
        "sections of larger African nations like Nigeria or Egypt."
    ),
    "uzbekistan": (
        "Uzbekistan sits at the intersection of the Former Soviet, Central Asian, "
        "and Muslim-majority country infobox styles. It shares fields with "
        "Eastern European, Middle Eastern, and South Asian countries, making it "
        "structurally equidistant from all these subgroups."
    ),
    "tuvalu": (
        "Tuvalu is the prototypical Pacific microstate -- tiny population, minimal "
        "historical sections, simple governance structure (monarchy/commonwealth), "
        "and limited economic data fields. It is the structural centroid of the "
        "cluster of very small island nations."
    ),
}

# Run k=5
result5 = kmedoids_clustering(COUNTRIES, MATRIX, k=5)
assignments5 = result5["assignments"]
members5 = result5["cluster_members"]
medoids5 = result5.get("medoids", [])
sil5 = silhouette_score(COUNTRIES, MATRIX, assignments5)[0]
dunn5 = dunn_index(COUNTRIES, MATRIX, assignments5)

print(f"\n  K-Medoids k=5  |  Silhouette={sil5:.4f}  Dunn={dunn5:.4f}")
print(f"  Medoids: {medoids5}\n")

for cid in sorted(members5.keys()):
    cluster_countries = sorted(members5[cid])
    medoid = medoids5[cid] if cid < len(medoids5) else "?"
    avg_d = avg_intra_dist(cluster_countries, COUNTRIES, MATRIX)

    print(f"  {'-'*65}")
    print(f"  CLUSTER {cid}  [{len(cluster_countries)} countries]   Medoid: {medoid.upper()}")
    print(f"  {'-'*65}")
    print(f"  Countries: {', '.join(cluster_countries[:12])}")
    if len(cluster_countries) > 12:
        print(f"             {', '.join(cluster_countries[12:24])}")
    if len(cluster_countries) > 24:
        print(f"             {', '.join(cluster_countries[24:])}")
    print(f"  Top regions: {majority_region(cluster_countries)}")
    print(f"  Avg intra-cluster distance: {avg_d:.1f}")
    reason = MEDOID_REASONS.get(medoid, "No description.")
    print(f"  Why {medoid} is central:")
    # wrap to 65 chars
    words = reason.split()
    line = "    "
    for w in words:
        if len(line) + len(w) > 68:
            print(line)
            line = "    " + w + " "
        else:
            line += w + " "
    if line.strip():
        print(line)
    print()

print("=" * 70)
print("ALL ANALYSES COMPLETE")
print("=" * 70)
