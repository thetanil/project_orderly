"""Issues 05 (CodeMirror editor) and 12 (# and @ completion)."""
from helpers import row

DESC = "aside .md[data-field=description] .cm-content"


def _open(ui, make_api=None):
    page, api = ui(make_api() if make_api else None)
    row(page, "ado-302").click()
    page.wait_for_selector(DESC)
    return page, api


def _desc(api):
    return next(i for i in api.snapshot()["items"] if i["id"] == "ado-302").get("description", "")


def test_editor_changes_are_saved_and_undone_by_the_app_level_undo(ui):
    page, api = _open(ui)
    before = _desc(api)
    page.click(DESC); page.keyboard.press("Control+End"); page.keyboard.type(" appended")
    page.click("button[title^='Redo']", force=True)  # blur the editor so its pending edit flushes
    page.wait_for_function("() => document.querySelector('button[title^=Undo]') && !document.querySelector('button[title^=Undo]').disabled")
    assert _desc(api).endswith("appended")
    page.click("button[title^='Undo']"); page.wait_for_timeout(300)
    assert _desc(api) == before
    shown = page.locator(DESC).inner_text().replace("Markdown (GFM). # for items, @ for people", "")  # placeholder of an empty editor
    assert " ".join(shown.split()) == " ".join(before.split())


def test_raw_html_typed_in_the_editor_shows_up_as_r22_in_problems(ui):
    page, api = _open(ui)
    page.click(DESC); page.keyboard.type("<b>bold</b>")
    page.click("button:has-text('Problems')")
    page.wait_for_selector("tbody tr:has-text('R22')")


def test_editor_follows_the_theme_toggle(ui):
    page, _ = _open(ui)
    bg = lambda: page.evaluate("getComputedStyle(document.querySelector('aside .md .cm-editor')).backgroundColor")
    dark = bg()
    page.click("button[title='Toggle theme']"); page.wait_for_timeout(200)
    light = bg()
    assert dark != light
    page.click("button[title='Toggle theme']"); page.wait_for_timeout(200)
    assert bg() == dark


def test_large_description_stays_responsive(ui, make_api):
    big = "\n".join(f"line {i} with some **markdown** and a [link](http://x)" for i in range(4000))
    page, api = ui(make_api(lambda d: d["items"]["ado-302"].update(description=big)))
    row(page, "ado-302").click(); page.wait_for_selector(DESC)
    page.click(DESC)
    ms = page.evaluate("""async () => {
        const t = performance.now();
        document.querySelector('aside .md[data-field=description] .cm-content').focus();
        await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
        return performance.now() - t;
    }""")
    page.keyboard.type("x")
    assert ms < 500, ms


def test_hash_offers_items(ui):
    page, api = _open(ui)
    page.click(DESC); page.keyboard.press("Control+End"); page.keyboard.type(" #ado-30")
    page.wait_for_selector(".cm-tooltip-autocomplete li:has-text('#ado-300')")


def test_at_offers_people(ui):
    page, api = _open(ui)
    pid = next(iter(api.snapshot()["people"]))
    page.click(DESC); page.keyboard.press("Control+End"); page.keyboard.type(" @")
    page.wait_for_selector(f".cm-tooltip-autocomplete li:has-text('@{pid}')")
