"""Issues 02 (Problems screen) and 09 (Fix buttons)."""
import re

from helpers import row


def _store_with_problems(make_api):
    def bad(d):
        d["items"]["ado-303"]["storyPoints"] = 5  # R7, fixable
        d["items"]["ado-302"]["description"] = "<b>hi</b>"  # R22, fixable
        d["items"]["ado-301"]["state"] = "Bogus"  # R3, not fixable

    return make_api(bad)


def test_problems_screen_lists_filters_and_counts_match_the_status_bar(ui, make_api):
    page, api = ui(_store_with_problems(make_api))
    issues = api.snapshot()["issues"]
    errors = [i for i in issues if i["level"] == "E"]
    warns = [i for i in issues if i["level"] == "W"]
    page.click("button:has-text('Problems')"); page.wait_for_selector("tbody tr")
    assert page.locator("tbody tr").count() == len(issues)
    head = page.locator("header").inner_text()
    assert (not errors) or f"⛔{len(errors)}" in head
    assert (not warns) or f"⚠{len(warns)}" in head

    page.locator(".bar select").nth(1).select_option("E")
    assert page.locator("tbody tr").count() == len(errors)
    page.locator(".bar select").nth(1).select_option("")
    page.locator(".bar select").nth(0).select_option("R7")
    assert page.locator("tbody tr").count() == 1
    assert re.search(r"1 of \d+", page.locator(".bar").inner_text())


def test_clicking_a_problem_jumps_to_the_item_field(ui, make_api):
    page, _ = ui(_store_with_problems(make_api))
    page.click("button:has-text('Problems')")
    page.click("tbody tr:has-text('R3')")
    page.wait_for_function("document.activeElement && document.activeElement.dataset.field === 'state'")
    assert page.locator("#tree").count() == 1  # back on the tree screen


def test_fix_button_appears_exactly_where_a_fix_exists(ui, make_api):
    page, api = ui(_store_with_problems(make_api))
    issues = api.snapshot()["issues"]
    assert any(i.get("fix") for i in issues) and any(not i.get("fix") for i in issues)
    page.click("button:has-text('Problems')"); page.wait_for_selector("tbody tr")
    for i in issues:
        tr = page.locator("tbody tr", has_text=i["rule"]).filter(has_text=i["itemId"] or "")
        assert (tr.locator("button:has-text('Fix')").count() == 1) == bool(i.get("fix")), i


def test_fix_button_resolves_the_problem_and_undo_brings_it_back(ui, make_api):
    page, api = ui(_store_with_problems(make_api))
    page.click("button:has-text('Problems')"); page.wait_for_selector("tbody tr")
    page.click("tbody tr:has-text('R22') button:has-text('Fix')")
    page.wait_for_function("!document.body.innerText.includes('R22')")
    assert "<b>" not in next(i for i in api.snapshot()["items"] if i["id"] == "ado-302")["description"]
    page.click("button[title^='Undo']"); page.wait_for_timeout(300)
    assert "R22" in {i["rule"] for i in api.snapshot()["issues"]}
    page.click("button:has-text('Problems')")
    page.wait_for_selector("tbody tr:has-text('R22')")
