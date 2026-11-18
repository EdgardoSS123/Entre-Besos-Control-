"""Order pricing on disposable SQLite and synthetic accounts. No production access."""
import copy
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request
import uuid
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path.cwd()
OUT = Path(os.environ.get('EB_PRICING_REVIEW', '/tmp/eb-pricing-review'))
OUT.mkdir(parents=True, exist_ok=True)
PUBLIC = Path(tempfile.mkdtemp(prefix='eb-pricing-public-'))
BASE = 'http://127.0.0.1:8893/'
for source in ROOT.iterdir():
    if source.suffix in ['.html', '.js', '.css', '.jpg', '.png', '.webmanifest']:
        shutil.copy(source, PUBLIC / source.name)
for directory in ['vendor', 'icons']:
    shutil.copytree(ROOT / directory, PUBLIC / directory)
shutil.copy(ROOT / 'control.html', PUBLIC / 'index.html')

seed = {
    'orderSalesVersion': 1,
    'lots': [
        {'id': lot, 'p': product, 'bottles': 120, 'ml': 700,
         'unitCost': 200, 'totalCost': 24000}
        for product, lot in enumerate(['ESP', 'CUP', 'DB'])
    ],
    'moves': [], 'contacts': [], 'materials': [], 'supplies': [],
    'inventoryOpenings': [
        {'lotId': lot, 'asOf': '2026-11-01', 'complete': True, 'inputRows': [],
         'rows': [{'location': 'CDMX', 'tag': 'Por clasificar',
                   'quantity': 120, 'sampleQuantity': 0}]}
        for lot in ['ESP', 'CUP', 'DB']
    ],
    'partnerOrders': [{
        'id': 'legacy-order', 'code': 'PED-0001', 'partner': 'edgardo',
        'customer': 'Synthetic legacy recipient', 'from': 'CDMX',
        'date': '2026-11-17', 'status': 'pending', 'quantity': 2,
        'lines': [{'product': 0, 'lotId': 'ESP', 'amount': '2',
                   'unit': 'bottle', 'quantity': 2}],
        'notes': '', 'version': 1, 'createdAt': '2026-11-17T15:00:00Z',
        'updatedAt': '2026-11-17T15:00:00Z', 'createdBy': 'esalazars',
        'updatedBy': 'esalazars', 'deliveredAt': None,
    }],
}

server_code = r'''
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');
const {createApp}=require('./server.cjs');
const salt='45'.repeat(16),hash=crypto.scryptSync('pricing-synthetic-only',Buffer.from(salt,'hex'),64,{N:32768,r:8,p:1,maxmem:67108864}).toString('hex');
const users=['esalazars','rsalazarm','msaenzc'].map(username=>({username,name:username,role:'editor',salt,hash}));
users.push({username:'socioEB2',name:'Synthetic reader',role:'reader',salt,hash});
createApp({folder:fs.mkdtempSync(path.join(os.tmpdir(),'eb-pricing-db-')),root:process.env.EB_TEST_PUBLIC,users,origins:['http://127.0.0.1:8893'],secure:false}).server.listen(8893,'127.0.0.1');
'''
server = subprocess.Popen(
    ['node', '--experimental-sqlite', '-e', server_code],
    env={**os.environ, 'EB_TEST_PUBLIC': str(PUBLIC)},
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
for attempt in range(80):
    try:
        urllib.request.urlopen(BASE + 'healthz', timeout=1)
        break
    except Exception:
        if server.poll() is not None:
            raise RuntimeError('Disposable pricing server exited before becoming ready')
        time.sleep(.1)
else:
    server.terminate()
    raise RuntimeError('Disposable pricing server did not become ready')


def login(context, user='esalazars'):
    response = context.request.post(
        BASE + 'api/login',
        data={'username': user, 'password': 'pricing-synthetic-only'},
        headers={'Origin': BASE[:-1]},
    )
    assert response.ok, response.text()
    return response.json()['csrf']


def cloud(context):
    response = context.request.get(BASE + 'api/state')
    assert response.ok, response.text()
    return response.json()


def ready(page):
    page.wait_for_function(
        "()=>window.EBShared&&!EBShared.pending&&!window.EBOrdersUI?.saving&&"
        "document.querySelector('#eb-cloud-state')?.textContent.startsWith('Actualizado')",
        timeout=20000,
    )


def saved(page):
    expect(page.locator('#order-dialog')).to_have_count(0, timeout=20000)
    ready(page)


def assert_money(container, subtotal, discount, total):
    for name, cents in [('subtotal', subtotal), ('discount', discount), ('total', total)]:
        expect(container.locator('[data-order-' + name + ']')).to_contain_text(
            format(cents / 100, ',.2f')
        )


def assert_no_overflow(page):
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Page overflows viewport'
    if page.locator('#order-dialog').count():
        assert page.locator('#order-dialog').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1'), 'Dialog overflows viewport'


def storage_fill(page):
    return page.evaluate('''()=>{
      let count=0;const chunk='x'.repeat(16384);
      for(let i=0;i<10000;i++){try{localStorage.setItem('__pricing_quota_'+i,chunk);count++;}
      catch(e){if(e.name!=='QuotaExceededError')throw e;break;}}
      let low=0,high=32768;
      while(low+1<high){const mid=Math.floor((low+high)/2);
      try{localStorage.setItem('__pricing_quota_tail','x'.repeat(mid));low=mid;}
      catch(e){if(e.name!=='QuotaExceededError')throw e;high=mid;}}
      return count;
    }''')


try:
    with sync_playwright() as playwright:
        engine = os.environ.get('EB_BROWSER', 'chromium')
        launch = {}
        if engine == 'chromium':
            executable = shutil.which('chromium') or shutil.which('google-chrome')
            launch = {'args': ['--no-sandbox']}
            if executable:
                launch['executable_path'] = executable
        browser = getattr(playwright, engine).launch(**launch)
        context = browser.new_context(
            viewport={'width': 1440, 'height': 1000},
            is_mobile=engine == 'webkit', has_touch=engine == 'webkit',
        )
        csrf = login(context)
        response = context.request.put(
            BASE + 'api/state',
            data={'revision': 0, 'initialize': True, 'operation': str(uuid.uuid4()), 'data': seed},
            headers={'Origin': BASE[:-1], 'X-EB-CSRF': csrf},
        )
        assert response.ok, response.text()
        initial = cloud(context)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: dialog.accept())
        page.goto(BASE + 'orders.html?partner=edgardo')
        ready(page)

        # Legacy orders gain a displayed total without a write or inventory mutation.
        legacy = page.locator('[data-order="legacy-order"]')
        assert_money(legacy, 220000, 0, 220000)
        assert cloud(context) == initial
        assert_no_overflow(page)

        # Every line uses bottle pricing, including six bottles in one box.
        page.locator('#order-new').click()
        page.locator('#order-customer').fill('Synthetic three-variety order')
        page.locator('[data-amount]').fill('1')
        page.locator('[data-unit]').select_option('box')
        for product, amount in [('1', '2'), ('2', '3')]:
            page.locator('#order-add-line').click()
            page.locator('.order-line').last.locator('[data-product]').select_option(product)
            line = page.locator('.order-line').last
            line.locator('[data-unit]').select_option('bottle')
            line.locator('[data-amount]').fill(amount)
        expect(page.locator('#order-dialog [data-line-price]')).to_have_count(3)
        preview = page.locator('#order-pricing-preview')
        assert_money(preview, 1165000, 0, 1165000)
        page.locator('#order-discount-type').select_option('percent')
        page.locator('#order-discount-value').fill('10')
        assert_money(preview, 1165000, 116500, 1048500)
        page.set_viewport_size({'width': 390, 'height': 844})
        assert_no_overflow(page)
        preview.scroll_into_view_if_needed()
        page.screenshot(path=str(OUT / (engine + '-pricing-preview-mobile.png')), full_page=True)

        # Invalid discounts never reach the shared workspace or close the form.
        before_invalid = cloud(context)
        for kind, value in [('percent', '-1'), ('percent', '101'), ('amount', '11650.01')]:
            page.locator('#order-discount-type').select_option(kind)
            page.locator('#order-discount-value').fill(value)
            page.locator('#order-save').click()
            expect(page.locator('#order-dialog')).to_be_visible()
            expect(page.locator('#order-error')).to_be_visible()
            expect(page.locator('#order-error')).not_to_have_text('')
            assert cloud(context) == before_invalid
        page.locator('#order-discount-type').select_option('percent')
        page.locator('#order-discount-value').fill('10')
        page.locator('#order-save').click()
        saved(page)
        data = cloud(context)['data']
        order = next(row for row in data['partnerOrders'] if row['id'] != 'legacy-order')
        order_id = order['id']
        assert order['subtotalCents'] == 1165000
        assert order['discountCents'] == 116500
        assert order['totalCents'] == 1048500
        assert data.get('lotStockAdjustments', []) == []
        record = page.locator('[data-order="' + order_id + '"]')
        assert_money(record, 1165000, 116500, 1048500)
        page.reload()
        ready(page)
        assert_money(record, 1165000, 116500, 1048500)

        # Deliver once, with linked sales adding up exactly to the discounted total.
        page.locator('[data-deliver="' + order_id + '"]').click()
        expect(record.locator('.order-status')).to_have_text('Entregado', timeout=20000)
        ready(page)
        delivered = cloud(context)['data']
        debits = copy.deepcopy(delivered['lotStockAdjustments'])
        assert sum(-row['delta'] for row in debits if row.get('status') != 'cancelled') == 11
        sales = [row for row in delivered['lotSales'] if row.get('orderId') == order_id and row.get('status') != 'cancelled']
        assert len(sales) == 3
        assert sum(row['totalCents'] for row in sales) == 1048500
        assert all(row['stockEffect'] is False and row['priceKnown'] for row in sales)
        assert all(not row.get('payments') for row in sales)
        sale_ids = sorted(row['id'] for row in sales)

        # A fixed peso discount updates money, never the existing stock exits.
        page.locator('[data-edit-order="' + order_id + '"]').click()
        expect(page.locator('#order-discount-type')).to_have_value('percent')
        expect(page.locator('#order-discount-value')).to_have_value(re.compile(r'10(?:\.0+)?'))
        page.locator('#order-discount-type').select_option('amount')
        page.locator('#order-discount-value').fill('500')
        assert_money(preview, 1165000, 50000, 1115000)
        page.locator('#order-save').click()
        saved(page)
        current = cloud(context)['data']
        assert current['lotStockAdjustments'] == debits
        sales = [row for row in current['lotSales'] if row.get('orderId') == order_id and row.get('status') != 'cancelled']
        assert sorted(row['id'] for row in sales) == sale_ids
        assert sum(row['totalCents'] for row in sales) == 1115000
        assert_money(record, 1165000, 50000, 1115000)
        page.set_viewport_size({'width': 1440, 'height': 1000})
        assert_no_overflow(page)
        page.screenshot(path=str(OUT / (engine + '-pricing-order-desktop.png')), full_page=True)

        other = browser.new_context(viewport={'width': 390, 'height': 844})
        login(other, 'rsalazarm')
        other_page = other.new_page()
        other_page.on('pageerror', lambda error: errors.append(str(error)))
        other_page.goto(BASE + 'orders.html?partner=edgardo')
        ready(other_page)
        assert_money(other_page.locator('[data-order="' + order_id + '"]'), 1165000, 50000, 1115000)
        assert cloud(other)['data'] == current
        assert_no_overflow(other_page)
        other_page.screenshot(path=str(OUT / (engine + '-pricing-shared-mobile.png')), full_page=True)
        other.close()

        # No discount restores full price; failed full-storage save keeps the same ID.
        page.evaluate("localStorage.setItem('eb-before-pricing-test','ORIGINAL KEEP')")
        assert storage_fill(page) > 100
        page.locator('[data-edit-order="' + order_id + '"]').click()
        # A stale invalid value in the disabled/hidden field must not block no-discount.
        page.locator('#order-discount-type').select_option('percent')
        page.locator('#order-discount-value').fill('-1')
        page.locator('#order-discount-type').select_option('none')
        expect(page.locator('#order-discount-value')).to_be_disabled()
        assert_money(preview, 1165000, 0, 1165000)
        fail_upload = {'value': True}

        def route(request):
            if request.request.method == 'PUT' and fail_upload['value']:
                request.fulfill(status=503, content_type='application/json', body='{"error":"Synthetic pricing offline"}')
            else:
                request.continue_()

        page.route('**/api/state', route)
        page.locator('#order-save').click()
        expect(page.locator('#order-error')).to_contain_text('este dispositivo', timeout=15000)
        expect(page.locator('#order-dialog')).to_be_visible()
        expect(page.locator('#order-discount-type')).to_have_value('none')
        assert cloud(context)['data'] == current
        pending = page.evaluate('(id)=>JSON.parse(localStorage.getItem("eb-v1")).partnerOrders.find(o=>o.id===id)', order_id)
        assert pending['totalCents'] == 1165000
        page.screenshot(path=str(OUT / (engine + '-pricing-quota-retry.png')), full_page=True)
        fail_upload['value'] = False
        page.locator('#order-save').click()
        saved(page)
        final = cloud(context)['data']
        final_order = next(row for row in final['partnerOrders'] if row['id'] == order_id)
        assert final_order == pending
        assert len(final['partnerOrders']) == 2
        assert final['lotStockAdjustments'] == debits
        assert sum(row['totalCents'] for row in final['lotSales'] if row.get('orderId') == order_id and row.get('status') != 'cancelled') == 1165000
        assert page.evaluate("localStorage.getItem('eb-before-pricing-test')") == 'ORIGINAL KEEP'
        assert_money(record, 1165000, 0, 1165000)
        page.reload()
        ready(page)
        assert_money(record, 1165000, 0, 1165000)
        assert cloud(context)['data'] == final
        for field in ['lots', 'moves', 'materials', 'supplies', 'inventoryOpenings']:
            assert final[field] == seed[field], field
        assert final['partnerOrders'][0] == seed['partnerOrders'][0]
        assert not errors, errors
        print('PASS ' + engine + ': bottle/box prices; three-product subtotal; percentage and peso discounts; invalid values blocked; persisted reload and second editor; exact linked sales; no stock rewrite; full-storage failure retained and retried once; legacy records and original data preserved.', flush=True)
        context.close()
        browser.close()
finally:
    server.terminate()
    server.wait(timeout=10)
