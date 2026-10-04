from __future__ import annotations

from itertools import combinations, product
import random
import string

import pytest

from playtrace.classify.resolver import ResolvedTitle, TitleResolver
from playtrace.models.enums import Classification, ConfidenceLevel


def _titles(names: list[str], launcher: str | None = None) -> list[ResolvedTitle]:
    return [
        ResolvedTitle(
            title_id=f"title:{index}", title=name,
            classification=Classification.GAME,
            classification_confidence=ConfidenceLevel.HIGH,
            title_confidence=ConfidenceLevel.HIGH, launcher=launcher,
            primary_exe_id=f"exe:{index}",
        )
        for index, name in enumerate(names)
    ]


def _verified_pairs(resolver: TitleResolver, titles: list[ResolvedTitle]) -> set[tuple[int, int]]:
    return {
        pair for pair in resolver._duplicate_candidate_pairs(titles)
        if resolver._duplicate_reasons(titles[pair[0]], titles[pair[1]])
    }


@pytest.mark.parametrize("names", [
    ["EldenRingDeluxe", "EldenRing"],
    ["ab", "ZabXXXX"],
    ["abcdefg", "axbxcxdxexfxg"],  # Exactly .70, no shared bigram.
    ["xbcdxfghxjkl", "abcdxfghxjky"],  # Neither head nor tail agrees.
    ["Pókemon", "Pokemon"],
    ["ELDEN RING", "Elden Ring"],
    ["a", "a" + "z" * 100],  # Containment must bypass length/overlap gates.
])
def test_blocking_preserves_title_anchors(names: list[str]) -> None:
    titles = _titles(names)
    resolver = TitleResolver()
    assert resolver._duplicate_reasons(*titles)
    assert _verified_pairs(resolver, titles) == {(0, 1)}
    assert len(resolver._duplicate_candidates(titles)) == 1


def test_dense_buckets_do_not_remove_existing_fuzzy_pairs() -> None:
    names = ["Final Fantasy"] + [f"Final Fantasy {index:02}" for index in range(30)]
    titles = _titles(names)
    resolver = TitleResolver()
    expected = {pair for pair in combinations(range(len(titles)), 2)
                if resolver._duplicate_reasons(titles[pair[0]], titles[pair[1]])}
    assert _verified_pairs(resolver, titles) == expected


def test_blocking_matches_pairwise_oracle_for_exhaustive_short_titles() -> None:
    names = [""] + ["".join(chars) for size in range(1, 6) for chars in product("ab", repeat=size)]
    titles = _titles(names)
    resolver = TitleResolver()
    expected = {pair for pair in combinations(range(len(titles)), 2)
                if resolver._duplicate_reasons(titles[pair[0]], titles[pair[1]])}
    assert _verified_pairs(resolver, titles) == expected


def test_blocking_matches_pairwise_oracle_for_seeded_variants() -> None:
    rng = random.Random(901)
    names = ["", "!!!", "中文", "Balatro", "Balatroo", "tide", "diet"]
    for _ in range(100):
        base = "".join(rng.choices(string.ascii_lowercase, k=rng.randrange(3, 50)))
        names.extend([base, base[:2] + "x" + base[3:], "xx" + base + "yy"])
    rng.shuffle(names)
    titles = _titles(names)
    resolver = TitleResolver()
    expected = {pair for pair in combinations(range(len(titles)), 2)
                if resolver._duplicate_reasons(titles[pair[0]], titles[pair[1]])}
    actual = list(resolver._duplicate_candidate_pairs(titles))
    assert len(actual) == len(set(actual))
    assert all(left < right for left, right in actual)
    assert _verified_pairs(resolver, titles) == expected


def test_launcher_is_supporting_evidence_only() -> None:
    resolver = TitleResolver()
    assert resolver._duplicate_candidates(_titles(["Alpha Protocol", "Balatro"], "Steam")) == []
    candidates = resolver._duplicate_candidates(_titles(["Elden Ring", "Elden Ring Deluxe"], "Steam"))
    assert candidates[0].reasons == ["metadata-backed title similarity", "shared launcher ancestry"]


def test_primary_has_direct_evidence_for_every_related_title() -> None:
    titles = _titles(["Alpha", "Alpha Beta", "Beta Gamma", "Gamma"])
    titles[0].title_confidence = ConfidenceLevel.HIGH
    for title in titles[1:]:
        title.title_confidence = ConfidenceLevel.LOW
    resolver = TitleResolver()
    by_id = {title.title_id: title for title in titles}
    candidates = resolver._duplicate_candidates(titles)
    seen: set[str] = set()
    for candidate in candidates:
        primary = by_id[candidate.primary_title_id]
        members = {candidate.primary_title_id, *candidate.related_title_ids}
        assert not seen.intersection(members)
        seen.update(members)
        assert candidate.related_title_ids
        for related_id in candidate.related_title_ids:
            assert resolver._duplicate_reasons(primary, by_id[related_id])
    assert candidates == resolver._duplicate_candidates(titles)


def test_unrelated_titles_reduce_verification_work() -> None:
    class CountingResolver(TitleResolver):
        calls = 0

        def _duplicate_reasons(self, left: ResolvedTitle, right: ResolvedTitle) -> list[str]:
            self.calls += 1
            return super()._duplicate_reasons(left, right)

    rng = random.Random(42)
    titles = _titles(["".join(rng.choices(string.ascii_lowercase, k=24)) for _ in range(200)])
    resolver = CountingResolver()
    assert resolver._duplicate_candidates(titles) == []
    assert resolver.calls < 200  # Pairwise baseline: 19,900 verifications.
