"""The wake-word matcher is a pure function — so it gets deterministic evals.
Whisper mangles phrases in predictable ways; these cases pin the fuzziness."""

import pytest

from pikaka.gateway.voice import matches_wake

SHOULD_WAKE = [
    ("pikaka pikaka", "pikaka pikaka"),
    ("Pikaka, pikaka!", "pikaka pikaka"),            # punctuation
    ("pikakapikaka", "pikaka pikaka"),               # whisper drops the space
    ("so anyway pikaka pikaka schedule it", "pikaka pikaka"),  # embedded in speech
    ("pikata pikaka", "pikaka pikaka"),            # one-letter mangle → fuzzy match
    ("Hey Pikaka", "hey pikaka"),
    ("hey computer, what's up", "hey computer"),
    # regression from the first live session: whisper wrote the wake word in
    # kana — variants after a comma cover other scripts
    ("ぴかぴか", "pikaka pikaka,ぴかぴか"),
    ("ぴかぴかぴか", "pikaka pikaka,ぴかぴか"),
    ("小助手你好", "pikaka pikaka,小助手"),
]

SHOULD_NOT_WAKE = [
    ("what a nice day", "pikaka pikaka"),
    ("wake up call at nine", "pikaka pikaka"),
    ("", "pikaka pikaka"),
    ("pikaka pikaka", ""),                        # no wake word configured
    ("walk to work", "pikaka pikaka"),
]


@pytest.mark.parametrize("heard,wake", SHOULD_WAKE, ids=[h for h, _ in SHOULD_WAKE])
def test_wakes(heard, wake):
    assert matches_wake(heard, wake)


@pytest.mark.parametrize("heard,wake", SHOULD_NOT_WAKE, ids=[h or "empty" for h, _ in SHOULD_NOT_WAKE])
def test_stays_asleep(heard, wake):
    assert not matches_wake(heard, wake)
