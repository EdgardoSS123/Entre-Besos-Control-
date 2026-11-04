"""Regression checks with isolated browser storage; never writes to an account."""
import os
import shutil
from playwright.sync_api import sync_playwright, expect

URL = os.environ.get('EB_TEST_URL', 'http://127.0.0.1:8765/')
with sync_playwright() as p:
    options = {'headless': True}
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if chrome:
        options['executable_path'] = chrome
    browser = p.chromium.launch(**options)
    for width, height in [(1440, 1000), (390, 844)]:
        mobile = width < 700
        ctx = browser.new_context(viewport={'width': width, 'height': height},
                                  is_mobile=mobile, has_touch=mobile)
        page = ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(URL, wait_until='networkidle')
        if page.locator('#list-new').count(): page.locator('#list-new').click()
        page.locator('#lot-id').wait_for()
        assert page.locator('#zero-on-edit').count() == 1, 'Published zero helper missing'
        page.locator('#lot-id').fill('ZERO-UI-TEST')
        page.locator('#producedLiters').fill('432')
        page.locator('#liquid').fill('200')
        expect(page.locator('#unit-total')).to_have_text('$144.00')
        for i in range(13):
            f = page.locator('#amount-' + str(i))
            expect(f).to_have_value('0')
            f.tap() if mobile else f.click()
            expect(f).to_have_value('')
            page.locator('#lot-id').click()
            expect(f).to_have_value('0')
        f = page.locator('#amount-0')
        f.tap() if mobile else f.click()
        f.press_sequentially('25.50')
        expect(f).to_have_value('25.50')
        expect(page.locator('#per-0')).to_have_text('$25.50')
        expect(page.locator('#unit-total')).to_have_text('$169.50')
        page.locator('#lot-id').click()
        f.tap() if mobile else f.click()
        expect(f).to_have_value('25.50')
        page.locator('#amount-1').fill('0.00')
        page.locator('#lot-id').click()
        page.locator('#amount-1').click()
        expect(page.locator('#amount-1')).to_have_value('')
        page.keyboard.press('Tab')
        expect(page.locator('#amount-1')).to_have_value('0')
        page.locator('#lossLiters').click()
        expect(page.locator('#lossLiters')).to_have_value('')
        page.locator('#lot-id').click()
        expect(page.locator('#lossLiters')).to_have_value('0')
        page.locator('#bottles').click()
        expect(page.locator('#bottles')).to_have_value('600')
        page.locator('#amount-2').click()
        page.locator('#amount-2').press_sequentially('0')
        expect(page.locator('#amount-2')).to_have_value('0')
        page.locator('#lot-id').click()
        page.locator('#amount-3').click()
        expect(page.locator('#amount-3')).to_have_value('')
        save = '#mobile-save-button' if mobile else '#save-lot'
        page.locator(save).dispatch_event('click')
        expect(page.locator('.saved-lot')).to_have_count(1)
        lots = page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).lots")
        assert lots[0]['components'][0] == 25.5
        assert lots[0]['components'][3] == 0
        assert lots[0]['unitCost'] == 169.5
        page.reload(wait_until='networkidle')
        expect(page.locator('h1')).to_have_text('Mis lotes')
        assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).lots[0].unitCost") == 169.5
        if page.locator('#show-lots').count(): page.locator('#show-lots').click()
        if page.locator('[data-edit="ZERO-UI-TEST"]').count():
            page.locator('[data-edit="ZERO-UI-TEST"]').click()
        else:
            page.locator('[data-simple-open="ZERO-UI-TEST"]').click()
            page.locator('#simple-costs').click()
        page.locator('#amount-0').click()
        expect(page.locator('#amount-0')).to_have_value('25.5')
        page.locator('#amount-1').click()
        expect(page.locator('#amount-1')).to_have_value('')
        page.locator('#lot-id').click()
        expect(page.locator('#amount-1')).to_have_value('0')
        assert not errors, errors
        print('PASS ZERO EDIT', width, ': all 13 costs, tap/click, decimals, tab, restore, nonzero protection, save and reload')
        ctx.close()
    browser.close()
