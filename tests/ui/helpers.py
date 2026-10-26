def rows(page):
    return page.locator("#tree .row")


def row(page, item_id):
    return page.locator("#tree .row", has=page.locator(f".id:text-is('{item_id}')"))


def status(page):
    return page.locator("footer").inner_text()
