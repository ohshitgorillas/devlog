"""Behavior tests for read commands: show, find, within, list, last."""

from __future__ import annotations

import datetime as dt
import json


def test_find_matches_body_case_insensitive(run, topic, find_json):
    run("add", "-T", topic, "-t", "t", "-e", "Needle Body Marker")
    assert len(find_json("needle")) == 1


def test_find_multi_term_requires_all(run, topic, find_json):
    run("add", "-T", topic, "-t", "a", "-e", "alpha bravo charlie")
    run("add", "-T", topic, "-t", "b", "-e", "alpha only")
    assert len(find_json("alpha", "bravo")) == 1


def test_find_in_title_excludes_body_matches(run, topic):
    run("add", "-T", topic, "-t", "title-marker", "-e", "x")
    run("add", "-T", topic, "-t", "other", "-e", "title-marker")
    r = run("find", "title-marker", "--in", "title", "--json")
    assert len(json.loads(r.stdout)) == 1


def test_find_limit_caps_results(run, topic):
    for i in range(4):
        run("add", "-T", topic, "-t", f"t{i}", "-e", "shared-marker")
    r = run("find", "shared-marker", "--limit", "2", "--json")
    assert len(json.loads(r.stdout)) == 2


def test_find_within_includes_recent_entry(run, topic):
    run("add", "-T", topic, "-t", "recent", "-e", "win-marker")
    r = run("find", "win-marker", "--within", "1d", "--json")
    assert len(json.loads(r.stdout)) == 1


def test_find_no_match_json_returns_empty_list(run, topic):
    r = run("find", "no-such-thing", "--json")
    assert json.loads(r.stdout) == []


def test_find_no_match_text_exits_nonzero(run, topic):
    r = run("find", "no-such-thing")
    assert r.returncode != 0


def test_show_iso_date_returns_todays_entry(run, topic):
    run("add", "-T", topic, "-t", "today", "-e", "x")
    today = dt.date.today().isoformat()
    r = run("show", today, "--json")
    titles = [e["title"] for e in json.loads(r.stdout)]
    assert "today" in titles


def test_show_mmdd_resolves_today(run, topic):
    run("add", "-T", topic, "-t", "mmdd-target", "-e", "x")
    today = dt.date.today()
    mmdd = f"{today.month:02d}{today.day:02d}"
    r = run("show", mmdd, "--json")
    titles = [e["title"] for e in json.loads(r.stdout)]
    assert "mmdd-target" in titles


def test_within_includes_recent_entry(run, topic):
    run("add", "-T", topic, "-t", "fresh", "-e", "x")
    r = run("within", "1d", "--json")
    titles = [e["title"] for e in json.loads(r.stdout)]
    assert "fresh" in titles


def test_list_includes_added_title(run, topic):
    run("add", "-T", topic, "-t", "list-target", "-e", "x")
    r = run("list", "--json")
    titles = [e["title"] for e in json.loads(r.stdout)]
    assert "list-target" in titles


def test_last_returns_newest_title(run, topic, last_json):
    run("add", "-T", topic, "-t", "older", "-e", "x")
    run("add", "-T", topic, "-t", "newest", "-e", "y")
    assert last_json()["title"] == "newest"


def test_topic_filter_restricts_find(run, topic):
    run("topic", "add", "Other")
    run("add", "-T", topic, "-t", "in-notes", "-e", "shared")
    run("add", "-T", "Other", "-t", "in-other", "-e", "shared")
    r = run("find", "shared", "-T", topic, "--json")
    titles = [e["title"] for e in json.loads(r.stdout)]
    assert titles == ["in-notes"]


def test_folder_qualified_topic_round_trips(run, vault):
    (vault / "Sub").mkdir()
    run("topic", "add", "Logs", "-F", "Sub")
    run("add", "-T", "Sub:Logs", "-t", "in-sub", "-e", "x")
    r = run("last", "-T", "Sub:Logs", "--json")
    assert json.loads(r.stdout)["title"] == "in-sub"


def test_folder_only_T_rejected_on_add(run, vault):
    (vault / "Sub").mkdir()
    r = run("add", "-T", "Sub:", "-t", "t", "-e", "x")
    assert r.returncode != 0


def test_default_folder_resolves_bare_topic(run, vault):
    (vault / "Sub").mkdir()
    run("config", "default-folder", "Sub")
    run("topic", "add", "Notes")
    run("add", "-T", "Notes", "-t", "in-default", "-e", "x")
    r = run("last", "-T", "Notes", "--json")
    assert json.loads(r.stdout)["title"] == "in-default"
