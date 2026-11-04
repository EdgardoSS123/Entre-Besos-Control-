"""Isolated browser profiles only. Never reads or changes a user's browser data."""
import os, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE=os.environ.get('EB_TEST_URL','http://127.0.0.1:8765/')
OUT=Path(os.environ.get('EB_SCREENSHOTS','/tmp/eb-location-screens')); OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('google-chrome'),headless=True,args=['--no-sandbox'])
    for width,height in [(1440,1000),(390,844)]:
        ctx=browser.new_context(viewport={'width':width,'height':height},is_mobile=width<700,has_touch=width<700)
        page=ctx.new_page(); errors=[]; page.on('pageerror',lambda e: errors.append(str(e)))
        page.goto(BASE+'?check=location-entry1',wait_until='networkidle')
        page.wait_for_function("document.documentElement.dataset.lotEntryFlow === '1'")
        old={'id':'UNCHANGED-TEST','p':0,'date':'2026-01-01','ml':720,'bottles':12,'unitCost':90,'totalCost':1080}
        seed={'lots':[old],'moves':[],'contacts':[{'name':'Synthetic preservation record'}],'costs':{},'documents':[{'test':'untouched'}]}
        page.evaluate("d=>localStorage.setItem('eb-v1',JSON.stringify(d))",seed)
        page.reload(); page.locator('#lot-id').wait_for()
        assert page.locator('#open-lot-stock').is_enabled()
        page.locator('#open-lot-stock').click()
        assert page.locator('#form-errors').is_visible()
        assert page.locator('#opening-panel').count()==0
        assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1'))")==seed
        page.locator('#lot-id').fill('TEST-LOCATION-01')
        page.locator('#producedLiters').fill('500'); page.locator('#lossLiters').fill('10')
        page.locator('#liquid').fill('200'); page.locator('#amount-0').fill('20')
        cost=page.evaluate('EBCosts.calc(draft).unit')
        page.reload(); page.locator('#lot-id').wait_for()
        assert page.locator('#lot-id').input_value()=='TEST-LOCATION-01'
        assert page.locator('#amount-0').input_value()=='20'
        page.locator('#open-lot-stock').click(); page.locator('#opening-panel').wait_for()
        saved=page.evaluate("JSON.parse(localStorage.getItem('eb-v1'))")
        assert len(saved['lots'])==2 and saved['lots'][0]==old
        assert saved['lots'][1]['unitCost']==cost and saved['lots'][1]['bottles']==680
        assert saved.get('inventoryOpenings',[])==[]
        assert saved['contacts']==seed['contacts'] and saved['documents']==seed['documents']
        rows=page.locator('.opening-row')
        rows.nth(0).locator('[data-tag]').select_option('Nacional')
        rows.nth(0).locator('[data-amount]').fill('50'); rows.nth(0).locator('[data-unit]').select_option('box')
        rows.nth(1).locator('[data-tag]').select_option('Exportación')
        rows.nth(1).locator('[data-amount]').fill('10'); rows.nth(1).locator('[data-unit]').select_option('box')
        page.locator('#opening-complete').check(); page.locator('#save-opening').click()
        assert page.evaluate("EBLedger.balance(JSON.parse(localStorage.getItem('eb-v1')),'TEST-LOCATION-01').total")==360
        before=page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).inventoryOpenings")
        page.locator('#stock-edit-cost').click(); page.locator('#amount-0').fill('21')
        page.locator('#open-lot-stock').click(); page.locator('#new-shipment').wait_for()
        assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).inventoryOpenings")==before
        assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).lots[1].unitCost")==cost+1
        assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).lots[0]")==old
        page.locator('#new-shipment').click(); assert page.locator('#shipment-panel').is_visible()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(OUT/f'location-{width}.png'),full_page=True)
        page.locator('#stock-edit-cost').click()
        page.on('dialog',lambda dialog:dialog.accept())
        page.locator('#new-lot').click(); page.locator('#lot-id').fill('TEST-NO-SPACE')
        page.locator('#producedLiters').fill('432'); page.locator('#liquid').fill('100')
        raw=page.evaluate("localStorage.getItem('eb-v1')")
        page.evaluate("""()=>{const original=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k==='eb-v1')throw new DOMException('Synthetic quota test','QuotaExceededError');return original.call(this,k,v);};}""")
        page.locator('#open-lot-stock').click()
        assert page.locator('#lot-id').input_value()=='TEST-NO-SPACE'
        assert page.locator('#form-errors').is_visible() and page.locator('#opening-panel').count()==0
        assert page.evaluate("localStorage.getItem('eb-v1')")==raw
        assert not errors,errors
        print('PASS',width,'save-to-location, draft reload, opening balances, unchanged records, revision safety, storage failure')
        ctx.close()
    browser.close()
