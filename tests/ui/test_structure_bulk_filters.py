"""Issues 08 (drag and keyboard moves), 10 (filters), 11 (bulk), 06/07 through the window."""
from helpers import row, rows


def _child_order(api, parent):
    kids = [i for i in api.snapshot()["items"] if i.get("parent") == parent]
    return [k["id"] for k in sorted(kids, key=lambda k: k["rank"])]


def _with_second_feature(make_api):
    api = make_api()
    api.create("feature", "Second feature", "ado-200")
    return api


def test_rerank_by_keyboard_and_by_drag_give_the_same_order(ui, make_api):
    kb_page, kb_api = ui(make_api())
    kb_page.click(".row:has-text('ado-301')"); kb_page.locator("#tree").focus()
    kb_page.keyboard.press("Alt+ArrowDown"); kb_page.wait_for_timeout(300)

    dr_page, dr_api = ui(make_api())
    box = row(dr_page, "ado-302").bounding_box()
    row(dr_page, "ado-301").drag_to(row(dr_page, "ado-302"), target_position={"x": 80, "y": box["height"] - 3})
    dr_page.wait_for_timeout(300)

    assert _child_order(kb_api, "ado-300") == _child_order(dr_api, "ado-300")
    assert _child_order(kb_api, "ado-300") != _child_order(make_api(), "ado-300")  # it did move


def test_reparent_by_keyboard_and_by_drag_give_the_same_parent(ui, make_api):
    kb_page, kb_api = ui(_with_second_feature(make_api))
    kb_page.click(".row:has-text('ado-301')"); kb_page.locator("#tree").focus()
    kb_page.keyboard.press("Tab"); kb_page.wait_for_timeout(300)

    dr_page, dr_api = ui(_with_second_feature(make_api))
    row(dr_page, "ado-301").drag_to(row(dr_page, "new-second-feature"))
    dr_page.wait_for_timeout(300)

    parent = lambda api: next(i for i in api.snapshot()["items"] if i["id"] == "ado-301")["parent"]
    assert parent(kb_api) == parent(dr_api) == "new-second-feature"


def test_drag_to_a_wrong_level_is_not_a_drop_target(ui, make_api):
    page, api = ui(make_api())
    row(page, "ado-301").drag_to(row(page, "ado-100"))
    page.wait_for_timeout(300)
    assert next(i for i in api.snapshot()["items"] if i["id"] == "ado-301")["parent"] == "ado-300"


def test_create_remove_and_undo_through_the_window(ui):
    page, api = ui()
    page.on("dialog", lambda d: d.accept())  # "Delete permanently?" confirm
    page.click(".row:has-text('ado-300')"); page.locator("#tree").focus(); page.keyboard.press("n")
    page.fill("#n-title", "Brand new story"); page.select_option("#n-type", "story")
    page.click("button:has-text('Create')"); page.wait_for_selector(".row:has-text('new-brand-new-story')")
    page.locator("#tree").focus(); page.keyboard.press("Shift+Delete"); page.wait_for_timeout(300)  # never-synced: hard delete
    assert page.locator(".row:has-text('new-brand-new-story')").count() == 0
    page.click("button[title^='Undo']"); page.wait_for_selector(".row:has-text('new-brand-new-story')")
    page.click(".row:has-text('ado-302')"); page.locator("#tree").focus(); page.keyboard.press("Delete"); page.wait_for_timeout(300)
    assert next(i for i in api.snapshot()["items"] if i["id"] == "ado-302")["state"] == "Removed"  # synced: soft remove


def test_bulk_edit_is_one_undo_step_in_the_window(ui):
    page, api = ui()
    pr = lambda i: next(x for x in api.snapshot()["items"] if x["id"] == i).get("priority")
    before = (pr("ado-301"), pr("ado-302"))
    page.click(".row:has-text('ado-302')"); page.click(".row:has-text('ado-301')", modifiers=["Control"])
    page.wait_for_selector("text=2 items selected"); page.select_option("#b-prio", "1"); page.wait_for_timeout(300)
    assert (pr("ado-301"), pr("ado-302")) == (1, 1)
    page.click("button[title^='Undo']"); page.wait_for_timeout(300)
    assert (pr("ado-301"), pr("ado-302")) == before


def test_filters_narrow_the_tree_and_never_change_data(ui):
    page, api = ui()
    snap = api.snapshot()["items"]
    page.locator(".filters input[type=text], .filters input:not([type])").first.fill("stored")
    page.wait_for_timeout(200)
    assert rows(page).count() < 6 and row(page, "ado-302").count() == 1
    assert api.snapshot()["items"] == snap


def test_mine_filter_follows_the_current_user_and_is_disabled_without_one(ui):
    page, api = ui()
    assert page.locator("label:has-text('Mine') input").is_disabled()
    me = next(i for i in api.snapshot()["items"] if i.get("assignedTo"))["assignedTo"]
    page.select_option("header select", me); page.wait_for_timeout(300)
    page.check("label:has-text('Mine') input"); page.wait_for_timeout(200)
    mine = {i["id"] for i in api.snapshot()["items"] if i.get("assignedTo") == me}
    shown = {t.strip() for t in rows(page).locator(".id").all_inner_texts()}
    assert mine <= shown


def test_filtering_3000_items_stays_within_a_frame_or_two(ui):
    from project_orderly.api import open_store

    page, _ = ui(open_store(None, 3000))
    ms = page.evaluate("""async () => {
        const el = document.querySelector('.filters input[type=text], .filters input:not([type])');
        const t = performance.now();
        el.value = 'Story 1'; el.dispatchEvent(new Event('input', {bubbles: true}));
        await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
        return performance.now() - t;
    }""")
    assert ms < 100, f"filter update took {ms:.0f} ms"  # one frame is 16 ms; 100 ms leaves room for slow CI runners


def test_tab_shift_tab_alt_up_and_alt_down_round_trip(ui, make_api):
    page, api = ui(_with_second_feature(make_api))
    parent = lambda: next(i for i in api.snapshot()["items"] if i["id"] == "ado-301")["parent"]
    order = _child_order(api, "ado-300")
    page.click(".row:has-text('ado-301')"); page.locator("#tree").focus()
    page.keyboard.press("Alt+ArrowDown"); page.wait_for_timeout(300)
    assert _child_order(api, "ado-300") != order
    page.keyboard.press("Alt+ArrowUp"); page.wait_for_timeout(300)
    assert _child_order(api, "ado-300") == order
    page.keyboard.press("Tab"); page.wait_for_timeout(300)
    assert parent() == "new-second-feature"
    page.keyboard.press("Shift+Tab"); page.wait_for_timeout(300)
    assert parent() == "ado-300"
