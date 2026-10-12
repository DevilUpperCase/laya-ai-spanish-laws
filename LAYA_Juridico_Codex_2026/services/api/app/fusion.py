def fuse(rank_lists: list[list[str]], k: int = 60) -> list[tuple[str,float]]:
    if k <= 0:
        raise ValueError("k must be positive")
    scores = {}
    for rank_list in rank_lists:
        for rank,identifier in enumerate(dict.fromkeys(rank_list),1):
            scores[identifier] = scores.get(identifier,0) + 1 / (k + rank)
    return sorted(scores.items(),key=lambda item:(-item[1],item[0]))
