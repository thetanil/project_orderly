"""Issues 01 (shell, stress), 03 (corrupt file in the window), 04 (inline edit), 13 (shortcuts, palette)."""
import re

from helpers import row, rows, status
from project_orderly.api import open_store


def test_stress_3000_has_exactly_3000_items_no_errors_and_renders_a_window_of_rows(ui):
    page, api = ui(open_store(None, 3000))
    assert re.search(r"/ 3000 items", status(page)), status(page)
    assert "⛔" not in page.locator("header").inner_text()
    assert 0 < rows(page).count() < 300  # windowed, not 3000 DOM rows


def test_corrupt_file_shows_a_readable_message_and_the_window_survives(ui, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json")
    page, _ = ui(open_store(str(bad)), wait=False)
    page.wait_for_selector(".errbox")
    assert "JSON" in page.locator(".errbox").inner_text() or "json" in page.locator(".errbox").inner_text().lower()


def test_missing_schema_version_is_shown_as_a_message(ui, tmp_path):
    f = tmp_path / "v1.json"
    f.write_text('{"items": {}}')
    page, _ = ui(open_store(str(f)), wait=False)
    page.wait_for_selector(".errbox")
    assert "schemaVersion" in page.locator(".errbox").inner_text()


def test_inline_edit_title_state_priority_and_points(ui):
    page, api = ui()
    items = lambda: {i["id"]: i for i in api.snapshot()["items"]}
    r = row(page, "ado-302")
    r.locator(".title").dblclick()
    page.keyboard.press("Control+a"); page.keyboard.type("Renamed"); page.keyboard.press("Enter")
    page.wait_for_function("() => document.body.innerText.includes('Renamed')")
    assert items()["ado-302"]["title"] == "Renamed"

    r.locator(".chip").dblclick()
    page.locator("#tree select").select_option("Active")
    page.wait_for_timeout(300)
    assert items()["ado-302"]["state"] == "Active"

    r.locator(".num").first.dblclick()
    page.locator("#tree select").select_option("1")
    page.wait_for_timeout(300)
    assert items()["ado-302"]["priority"] == 1

    r.locator(".num").nth(1).dblclick()
    page.keyboard.type("8"); page.keyboard.press("Enter")
    page.wait_for_timeout(300)
    assert items()["ado-302"]["storyPoints"] == 8


def test_shortcuts_undo_redo_arrows_new_filter_and_next_problem(ui):
    page, api = ui()
    pts = lambda: next(i for i in api.snapshot()["items"] if i["id"] == "ado-302")["storyPoints"]
    start = pts()
    row(page, "ado-302").locator(".num").nth(1).dblclick()
    page.keyboard.type("13"); page.keyboard.press("Enter"); page.wait_for_timeout(300)
    assert pts() == 13
    page.locator("#tree").focus()
    page.keyboard.press("Control+z"); page.wait_for_timeout(300); assert pts() == start
    page.keyboard.press("Control+Shift+z"); page.wait_for_timeout(300); assert pts() == 13

    row(page, "ado-300").click()
    page.keyboard.press("ArrowDown")
    assert "cur" in row(page, "ado-303").get_attribute("class") or "cur" in (rows(page).nth(4).get_attribute("class") or "")
    page.keyboard.press("n"); page.wait_for_selector("#n-title")
    page.keyboard.press("Escape"); assert page.locator("#n-title").count() == 0
    page.locator("#tree").focus(); page.keyboard.press("/")
    assert page.evaluate("document.activeElement.tagName") == "INPUT"
    page.keyboard.press("Escape")
    assert page.evaluate("document.activeElement.id") == "tree"


def test_enter_edits_title_and_escape_cancels(ui):
    page, api = ui()
    row(page, "ado-302").click(); page.locator("#tree").focus()
    page.keyboard.press("Enter")
    page.keyboard.type("zzz"); page.keyboard.press("Escape")
    assert "zzz" not in page.locator("#tree").inner_text()
    assert next(i for i in api.snapshot()["items"] if i["id"] == "ado-302")["title"] != "zzz"


def test_palette_finds_an_item_by_id_and_by_title_in_the_stress_dataset(ui):
    page, api = ui(open_store(None, 3000))
    first = api.snapshot()["items"][0]
    page.keyboard.press("Control+k"); page.wait_for_selector(".modal input")
    page.keyboard.type(first["id"]); page.wait_for_selector(f".modal li:has-text('{first['id']}')")
    page.keyboard.press("Escape")
    page.keyboard.press("Control+k")
    word = first["title"].split()[0]
    page.keyboard.type(first["title"][:12]); page.wait_for_selector(f".modal li:has-text('{word}')")
    page.keyboard.press("Escape")
    assert page.locator(".modal").count() == 0


def test_palette_runs_actions(ui):
    page, _ = ui()
    page.keyboard.press("Control+k"); page.keyboard.type("problems"); page.keyboard.press("Enter")
    page.wait_for_selector("section .bar")


def test_f8_jumps_to_the_next_problem(ui, make_api):
    api = make_api(lambda d: d["items"]["ado-302"].update(state="Bogus"))  # R3: state not valid for the type
    page, _ = ui(api)
    page.keyboard.press("F8")
    page.wait_for_function("document.activeElement && document.activeElement.dataset.field === 'state'")
