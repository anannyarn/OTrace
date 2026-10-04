import pytest
from app.collectors.search_api import parse_profile_url


def test_valid_profile_urls():
    assert parse_profile_url("https://www.linkedin.com/in/arunnair/") == ("LinkedIn", "arunnair")
    assert parse_profile_url("https://in.linkedin.com/in/arun-nair-5485458") == ("LinkedIn", "arun-nair-5485458")
    assert parse_profile_url("https://instagram.com/arunnair_official") == ("Instagram", "arunnair_official")
    assert parse_profile_url("https://x.com/arun_dev") == ("X/Twitter", "arun_dev")
    assert parse_profile_url("https://facebook.com/arunnair.profile") == ("Facebook", "arunnair.profile")
    assert parse_profile_url("https://youtube.com/@arunnair_vlogs") == ("YouTube", "arunnair_vlogs")
    assert parse_profile_url("https://github.com/arunnair") == ("GitHub", "arunnair")
    assert parse_profile_url("https://www.reddit.com/user/arunnair_dev/") == ("Reddit", "arunnair_dev")
    assert parse_profile_url("https://medium.com/@arunnair") == ("Medium", "arunnair")
    assert parse_profile_url("https://www.kaggle.com/arunnair") == ("Kaggle", "arunnair")
    assert parse_profile_url("https://leetcode.com/u/arun_2292/") == ("LeetCode", "arun_2292")
    assert parse_profile_url("https://www.hackerrank.com/profile/arunnair") == ("HackerRank", "arunnair")


def test_invalid_post_and_feed_urls():
    assert parse_profile_url("https://www.linkedin.com/in/arunnair/posts/12345") is None
    assert parse_profile_url("https://instagram.com/p/B12345678") is None
    assert parse_profile_url("https://x.com/arun_dev/status/987654321") is None
    assert parse_profile_url("https://youtube.com/watch?v=12345") is None
    assert parse_profile_url("https://facebook.com/groups/12345") is None
    assert parse_profile_url("https://www.reddit.com/r/nitcalicut/") is None
    assert parse_profile_url("https://leetcode.com/problems/course-schedule-iv/") is None
