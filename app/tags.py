from __future__ import annotations


MAX_TAG_LENGTH = 40


def normalize_tag_name(value: str) -> str:
    normalized = " ".join(value.strip().lower().split())
    if not normalized:
        raise ValueError("Tags must not be blank")
    if len(normalized) > MAX_TAG_LENGTH:
        raise ValueError(f"Tags must not be longer than {MAX_TAG_LENGTH} characters")
    return normalized


def normalize_tag_names(values: list[str] | None) -> list[str]:
    if values is None:
        return []

    normalized_tags: list[str] = []
    seen: set[str] = set()

    for value in values:
        normalized = normalize_tag_name(value)
        if normalized in seen:
            continue
        seen.add(normalized)
        normalized_tags.append(normalized)

    return normalized_tags
