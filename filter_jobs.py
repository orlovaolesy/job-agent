def dedupe_and_sort(jobs):
    seen = set()
    unique = []
    for j in jobs:
        key = (j["title"], j["company"], j["link"])
        if key not in seen:
            seen.add(key)
            unique.append(j)
    return sorted(unique, key=lambda x: x.get("title", ""))
