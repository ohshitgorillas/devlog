"""Behavior tests for `tephra add`."""

from __future__ import annotations


def test_add_creates_entry(run, topic, last_json):
    run("add", "-T", topic, "-t", "first", "-e", "body")
    assert last_json()["title"] == "first"


def test_add_unknown_topic_exits_nonzero(run):
    r = run("add", "-T", "Ghost", "-t", "t", "-e", "x")
    assert r.returncode != 0


def test_duplicate_title_same_day_exits_nonzero(run, topic):
    run("add", "-T", topic, "-t", "dup", "-e", "first")
    r = run("add", "-T", topic, "-t", "dup", "-e", "second")
    assert r.returncode != 0


def test_duplicate_title_does_not_overwrite_body(run, topic, last_json):
    run("add", "-T", topic, "-t", "dup", "-e", "original-body")
    run("add", "-T", topic, "-t", "dup", "-e", "replacement-body")
    assert "original-body" in last_json()["body"]


def test_invalid_related_anchor_exits_nonzero(run, topic):
    r = run(
        "add", "-T", topic, "-t", "t", "-e", "x",
        "--related", f"{topic}#2026-01-01 — nonexistent",
    )
    assert r.returncode != 0


def test_valid_related_link_persisted(run, topic, last_json):
    run("add", "-T", topic, "-t", "first", "-e", "x")
    target = last_json()
    anchor = f"{topic}#{target['date']} {target['time']} — first"
    run("add", "-T", topic, "-t", "second", "-e", "y", "--related", anchor)
    assert any("first" in link for link in last_json()["related"])


def test_repeated_e_produces_ordered_paragraphs(run, topic, last_json):
    run("add", "-T", topic, "-t", "t", "-e", "para-one", "-e", "para-two")
    body = last_json()["body"]
    assert body.index("para-one") < body.index("para-two")


def test_dash_e_reads_stdin(run, topic, last_json):
    run("add", "-T", topic, "-t", "t", "-e", "-", stdin="from-stdin-body")
    assert "from-stdin-body" in last_json()["body"]


def test_html_token_auto_backticked(run, topic, last_json):
    run("add", "-T", topic, "-t", "t", "-e", "uses <name> token")
    assert "`<name>`" in last_json()["body"]
