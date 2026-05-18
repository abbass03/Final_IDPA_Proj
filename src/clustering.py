"""
Clustering algorithms operating on a precomputed distance matrix.

Algorithms:
  - Agglomerative Hierarchical Clustering (AHC) with single / complete / average linkage
  - K-Medoids (PAM)

Evaluation metrics:
  - Silhouette Score
  - Dunn Index
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_assignments(
    countries: list[str],
    clusters: dict[int, list[int]],
) -> tuple[dict[str, int], dict[int, list[str]]]:
    """Map representative-index clusters → country-name dicts."""
    assignments: dict[str, int] = {}
    members: dict[int, list[str]] = {}
    for cid, (_, indices) in enumerate(sorted(clusters.items())):
        country_list = [countries[i] for i in indices]
        members[cid] = country_list
        for c in country_list:
            assignments[c] = cid
    return assignments, members


# ---------------------------------------------------------------------------
# Agglomerative Hierarchical Clustering
# ---------------------------------------------------------------------------

def agglomerative_clustering(
    countries: list[str],
    dist_matrix: list[list[int]],
    n_clusters: int = 5,
    linkage: str = "average",
) -> dict:
    """
    Bottom-up AHC.

    Runs all N-1 merges so the full linkage matrix is available for dendrogram
    rendering. Cluster assignments are snapshotted the moment n_clusters remain.

    Parameters
    ----------
    countries    : ordered list of country names matching dist_matrix rows/cols
    dist_matrix  : symmetric NxN integer distance matrix (diagonal = 0)
    n_clusters   : number of clusters to cut the tree at
    linkage      : "single" | "complete" | "average"  (UPGMA)

    Returns
    -------
    dict with keys:
      algorithm      – "ahc"
      linkage        – linkage strategy used
      n_clusters     – k
      assignments    – {country: cluster_id}
      cluster_members– {cluster_id: [country, ...]}
      linkage_matrix – [[id_a, id_b, distance, new_size], ...]  (N-1 rows,
                        scipy-compatible format for dendrogram rendering)
    """
    linkage = linkage.lower()
    if linkage not in ("single", "complete", "average"):
        raise ValueError(f"linkage must be single | complete | average, got {linkage!r}")

    n = len(countries)
    if not 1 <= n_clusters <= n:
        raise ValueError(f"n_clusters must be in [1, {n}]")

    # Mutable working copy (floats so average linkage stays exact)
    dist: list[list[float]] = [
        [float(dist_matrix[i][j]) for j in range(n)] for i in range(n)
    ]

    # clusters[rep] = list of leaf indices assigned to this cluster
    clusters: dict[int, list[int]] = {i: [i] for i in range(n)}
    active: set[int] = set(range(n))

    # Node IDs for linkage matrix (leaves 0..n-1, internals n, n+1, ...)
    node_id: dict[int, int] = {i: i for i in range(n)}
    next_id: int = n

    linkage_matrix: list[list] = []
    saved_assignments: dict[str, int] | None = None
    saved_members: dict[int, list[str]] | None = None

    while len(active) > 1:
        # Snapshot assignments when we first reach exactly n_clusters
        if len(active) == n_clusters and saved_assignments is None:
            saved_assignments, saved_members = _extract_assignments(countries, clusters)

        # Find the closest pair of active clusters
        best_dist = float("inf")
        a = b = -1
        al = sorted(active)
        for ii in range(len(al)):
            ci = al[ii]
            for jj in range(ii + 1, len(al)):
                cj = al[jj]
                if dist[ci][cj] < best_dist:
                    best_dist = dist[ci][cj]
                    a, b = ci, cj

        size_a = len(clusters[a])
        size_b = len(clusters[b])

        # Record merge in scipy linkage format
        linkage_matrix.append([node_id[a], node_id[b], best_dist, size_a + size_b])

        # Update distances from merged cluster to every other active cluster
        for k in active:
            if k == a or k == b:
                continue
            if linkage == "single":
                nd = min(dist[a][k], dist[b][k])
            elif linkage == "complete":
                nd = max(dist[a][k], dist[b][k])
            else:  # average (UPGMA)
                nd = (size_a * dist[a][k] + size_b * dist[b][k]) / (size_a + size_b)
            dist[a][k] = dist[k][a] = nd

        # Absorb b into a
        clusters[a].extend(clusters.pop(b))
        active.discard(b)
        node_id[a] = next_id
        next_id += 1

    # Edge case: n_clusters == 1
    if saved_assignments is None:
        saved_assignments, saved_members = _extract_assignments(countries, clusters)

    return {
        "algorithm": "ahc",
        "linkage": linkage,
        "n_clusters": n_clusters,
        "assignments": saved_assignments,
        "cluster_members": saved_members,
        "linkage_matrix": linkage_matrix,
    }


# ---------------------------------------------------------------------------
# K-Medoids (PAM — Partitioning Around Medoids)
# ---------------------------------------------------------------------------

def _total_cost(
    medoids: list[int],
    dist_matrix: list[list[int]],
    n: int,
) -> tuple[float, list[int]]:
    """Assign each point to nearest medoid; return total cost and assignments."""
    assignments = [0] * n
    cost = 0.0
    for i in range(n):
        best = float("inf")
        for mid, m in enumerate(medoids):
            d = dist_matrix[i][m]
            if d < best:
                best = d
                assignments[i] = mid
        cost += best
    return cost, assignments


def kmedoids_clustering(
    countries: list[str],
    dist_matrix: list[list[int]],
    k: int,
) -> dict:
    """
    K-Medoids via PAM (Partitioning Around Medoids).

    BUILD phase  : greedy initialisation — pick medoids that minimise total
                   distance to all other points.
    SWAP phase   : for each (medoid, non-medoid) pair, accept the swap if it
                   reduces total cost. Repeat until no improvement.

    Parameters
    ----------
    countries   : ordered list of country names
    dist_matrix : symmetric NxN integer distance matrix
    k           : number of clusters

    Returns
    -------
    dict with keys:
      algorithm      – "kmedoids"
      n_clusters     – k
      medoids        – [country_name, ...]  one per cluster
      assignments    – {country: cluster_id}
      cluster_members– {cluster_id: [country, ...]}
      total_cost     – sum of distances from each point to its medoid
    """
    n = len(countries)
    if not 1 <= k <= n:
        raise ValueError(f"k must be in [1, {n}]")

    # --- BUILD phase: greedy medoid initialisation ---
    # First medoid: point with smallest sum of distances to all others
    row_sums = [sum(dist_matrix[i]) for i in range(n)]
    first = min(range(n), key=lambda i: row_sums[i])
    medoids = [first]

    # Each subsequent medoid: point that maximally reduces total cost
    for _ in range(k - 1):
        best_gain = -1.0
        best_candidate = -1
        for candidate in range(n):
            if candidate in medoids:
                continue
            # Cost reduction if candidate joins as a medoid
            gain = 0.0
            for i in range(n):
                current_best = min(dist_matrix[i][m] for m in medoids)
                new_best = min(current_best, dist_matrix[i][candidate])
                gain += current_best - new_best
            if gain > best_gain:
                best_gain = gain
                best_candidate = candidate
        medoids.append(best_candidate)

    # --- SWAP phase: iteratively improve ---
    current_cost, assignments = _total_cost(medoids, dist_matrix, n)

    improved = True
    while improved:
        improved = False
        for mi, medoid in enumerate(medoids):
            for candidate in range(n):
                if candidate in medoids:
                    continue
                trial_medoids = medoids[:mi] + [candidate] + medoids[mi + 1:]
                new_cost, new_assignments = _total_cost(trial_medoids, dist_matrix, n)
                if new_cost < current_cost - 1e-9:
                    medoids = trial_medoids
                    assignments = new_assignments
                    current_cost = new_cost
                    improved = True

    # Build output dicts
    cluster_members: dict[int, list[str]] = {cid: [] for cid in range(k)}
    country_assignments: dict[str, int] = {}
    for i, cid in enumerate(assignments):
        cluster_members[cid].append(countries[i])
        country_assignments[countries[i]] = cid

    return {
        "algorithm": "kmedoids",
        "n_clusters": k,
        "medoids": [countries[m] for m in medoids],
        "assignments": country_assignments,
        "cluster_members": cluster_members,
        "total_cost": current_cost,
    }


# ---------------------------------------------------------------------------
# Evaluation Metrics
# ---------------------------------------------------------------------------

def silhouette_score(
    countries: list[str],
    dist_matrix: list[list[int]],
    assignments: dict[str, int],
) -> tuple[float, dict[str, float]]:
    """
    Silhouette score for a clustering.

    For each point i:
      a(i) = mean distance to all points in the same cluster
      b(i) = min over other clusters of (mean distance to points in that cluster)
      s(i) = (b(i) - a(i)) / max(a(i), b(i))

    Returns overall mean silhouette and per-country scores.
    Score range: [-1, 1].  Higher is better.  >0.5 is considered good.
    """
    n = len(countries)
    labels = [assignments[c] for c in countries]
    k = max(labels) + 1

    # Group indices by cluster
    by_cluster: dict[int, list[int]] = {cid: [] for cid in range(k)}
    for i, cid in enumerate(labels):
        by_cluster[cid].append(i)

    per_country: dict[str, float] = {}

    for i, country in enumerate(countries):
        ci = labels[i]
        same = by_cluster[ci]

        # a(i): mean intra-cluster distance (excluding self)
        if len(same) <= 1:
            a = 0.0
        else:
            a = sum(dist_matrix[i][j] for j in same if j != i) / (len(same) - 1)

        # b(i): min mean distance to any other cluster
        b = float("inf")
        for cid, members in by_cluster.items():
            if cid == ci or not members:
                continue
            mean_d = sum(dist_matrix[i][j] for j in members) / len(members)
            if mean_d < b:
                b = mean_d

        if b == float("inf"):
            s = 0.0
        else:
            denom = max(a, b)
            s = (b - a) / denom if denom > 0 else 0.0

        per_country[country] = round(s, 6)

    overall = sum(per_country.values()) / n if n > 0 else 0.0
    return round(overall, 6), per_country


def dunn_index(
    countries: list[str],
    dist_matrix: list[list[int]],
    assignments: dict[str, int],
) -> float:
    """
    Dunn Index = min inter-cluster distance / max intra-cluster diameter.

    Higher is better.  Measures compactness vs separation.
    """
    labels = [assignments[c] for c in countries]
    k = max(labels) + 1
    n = len(countries)

    by_cluster: dict[int, list[int]] = {cid: [] for cid in range(k)}
    for i, cid in enumerate(labels):
        by_cluster[cid].append(i)

    # Max intra-cluster diameter (largest within-cluster distance)
    max_diameter = 0.0
    for members in by_cluster.values():
        for ii in range(len(members)):
            for jj in range(ii + 1, len(members)):
                d = dist_matrix[members[ii]][members[jj]]
                if d > max_diameter:
                    max_diameter = d

    if max_diameter == 0:
        return float("inf")

    # Min inter-cluster distance (smallest between-cluster distance)
    min_inter = float("inf")
    cluster_ids = list(by_cluster.keys())
    for ci in range(len(cluster_ids)):
        for cj in range(ci + 1, len(cluster_ids)):
            a_members = by_cluster[cluster_ids[ci]]
            b_members = by_cluster[cluster_ids[cj]]
            for ii in a_members:
                for jj in b_members:
                    d = dist_matrix[ii][jj]
                    if d < min_inter:
                        min_inter = d

    if min_inter == float("inf"):
        return 0.0

    return round(min_inter / max_diameter, 6)


# ---------------------------------------------------------------------------
# DBSCAN (Density-Based Spatial Clustering of Applications with Noise)
# ---------------------------------------------------------------------------

def dbscan_clustering(
    countries: list[str],
    dist_matrix: list[list[int]],
    eps: float,
    min_samples: int = 3,
) -> dict:
    """
    DBSCAN on a precomputed distance matrix.

    A point is a *core point* if it has >= min_samples points (including itself)
    within radius eps.  Border points are reachable from a core point but are not
    core points themselves.  All other points are *noise* (cluster id = -1).

    Parameters
    ----------
    countries   : ordered list of country names
    dist_matrix : symmetric NxN distance matrix
    eps         : neighbourhood radius
    min_samples : minimum neighbourhood size (including self) to be a core point

    Returns
    -------
    dict with keys:
      algorithm      – "dbscan"
      eps            – eps used
      min_samples    – min_samples used
      n_clusters     – number of clusters found (excluding noise)
      assignments    – {country: cluster_id}  (-1 = noise)
      cluster_members– {cluster_id: [country, ...]}  (noise not included)
      noise          – [country, ...]  points labelled as noise
      n_noise        – count of noise points
    """
    n = len(countries)

    # Precompute neighbour lists (excluding self)
    neighbors: list[list[int]] = []
    for i in range(n):
        nbrs = [j for j in range(n) if j != i and dist_matrix[i][j] <= eps]
        neighbors.append(nbrs)

    UNVISITED = -2
    NOISE = -1
    labels = [UNVISITED] * n
    cluster_id = 0

    for i in range(n):
        if labels[i] != UNVISITED:
            continue
        # +1 counts self
        if len(neighbors[i]) + 1 < min_samples:
            labels[i] = NOISE
            continue

        # Expand new cluster from core point i
        labels[i] = cluster_id
        queue = list(neighbors[i])
        qi = 0
        while qi < len(queue):
            q = queue[qi]
            qi += 1
            if labels[q] == NOISE:
                labels[q] = cluster_id      # border → member
            if labels[q] != UNVISITED:
                continue
            labels[q] = cluster_id
            if len(neighbors[q]) + 1 >= min_samples:   # q is also a core point
                queue.extend(neighbors[q])

        cluster_id += 1

    # Build output
    cluster_members: dict[int, list[str]] = {}
    noise: list[str] = []
    assignments: dict[str, int] = {}
    for i, cid in enumerate(labels):
        assignments[countries[i]] = cid
        if cid == NOISE:
            noise.append(countries[i])
        else:
            cluster_members.setdefault(cid, []).append(countries[i])

    return {
        "algorithm": "dbscan",
        "eps": eps,
        "min_samples": min_samples,
        "n_clusters": cluster_id,
        "assignments": assignments,
        "cluster_members": cluster_members,
        "noise": noise,
        "n_noise": len(noise),
    }
