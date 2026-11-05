"""Synthetic records in isolated browser profiles. Never accesses user data."""
import os,shutil,copy
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
URL=os.environ.get('EB_TEST_URL','http://127.0.0.1:8765/')
OUT=Path('/tmp/eb-lot-card-checks');OUT.mkdir(exist_ok=True)
fixture={'lots':[{'id':'CI-DB','p':2,'date':'2024-11-03','ml':720,'bottles':438,'producedLiters':350,'lossLiters':34,'remainingLiters':0.64,'productionMode':'liters','unitCost':237.66,'totalCost':104095.08}], 'moves':[], 'contacts':[{'preserve':'untouched'}], 'costs':{}, 'documents':[{'preserve':'untouched'}], 'inventoryOpenings':[{'lotId':'CI-DB','asOf':'2024-11-03','rows':[{'location':'CDMX','tag':'Por clasificar','quantity':394,'sampleQuantity':0}],'complete':False}]}
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),headless=True,args=['--no-sandbox'])
    for width,height in [(1440,1000),(390,844),(375,812)]:
        ctx=browser.new_context(viewport={'width':width,'height':height},is_mobile=width<700,has_touch=width<700)
        page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(URL,wait_until='networkidle');page.evaluate('(d)=>localStorage.setItem("eb-v1",JSON.stringify(d))',fixture);page.reload(wait_until='networkidle')
        card=page.locator('[data-lot-summary="CI-DB"]')
        expect(card.locator('.lot-card-cost-label')).to_have_text('COSTO POR BOTELLA')
        assert card.locator('.lot-card-cost-label').bounding_box()['y'] < card.locator('.price').bounding_box()['y']
        expect(card.locator('[data-summary-produced]')).to_have_text('438')
        expect(card.locator('[data-summary-current]')).to_have_text('394')
        assert '65 corrugados + 4 bot. sueltas' in card.inner_text()
        assert '44 botellas' in card.locator('.lot-card-warning').inner_text()
        assert page.evaluate('JSON.parse(localStorage.getItem("eb-v1"))')==fixture,'Display must not write'
        card.locator('[data-simple-open]').click()
        expect(page.locator('#simple-produced')).to_have_text('438');expect(page.locator('#simple-current')).to_have_text('394')
        page.locator('#simple-sale-tab').click();page.locator('#simple-amount').fill('25');page.locator('#simple-unit').select_option('bottle');page.locator('#simple-price').fill('1000');page.locator('#simple-save').click()
        expect(page.locator('#simple-current')).to_have_text('369');expect(page.locator('#simple-produced')).to_have_text('438')
        page.locator('#simple-sample-tab').click();page.locator('#simple-sample-action').select_option('consume');page.locator('#simple-amount').fill('6');page.locator('#simple-save').click()
        expect(page.locator('#simple-current')).to_have_text('363')
        page.locator('#simple-move-tab').click();page.locator('#simple-destination').select_option('USA');page.locator('#simple-amount').fill('5');page.locator('#simple-unit').select_option('bottle');page.locator('#simple-save').click()
        expect(page.locator('#simple-current')).to_have_text('363')
        page.locator('#simple-back').click()
        expect(card.locator('[data-summary-produced]')).to_have_text('438');expect(card.locator('[data-summary-current]')).to_have_text('363')
        assert '60 corrugados + 3 bot. sueltas' in card.inner_text()
        assert 'Vendidas: 25' in card.inner_text() and 'Muestras entregadas: 6' in card.inner_text()
        card.locator('.lot-card-calculation > summary').click()
        assert '394 bot.' in card.locator('dl').inner_text() and '-25 bot.' in card.locator('dl').inner_text() and '-6 bot.' in card.locator('dl').inner_text() and '363 bot.' in card.locator('dl').inner_text()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),'Horizontal overflow'
        page.screenshot(path=str(OUT/f'lot-cards-{width}.png'),full_page=True)
        snapshot=page.evaluate('JSON.parse(localStorage.getItem("eb-v1"))');page.reload(wait_until='networkidle')
        expect(card.locator('[data-summary-current]')).to_have_text('363')
        assert page.evaluate('JSON.parse(localStorage.getItem("eb-v1"))')==snapshot
        page.locator('#search-lots').fill('CI');page.locator('#search-lots').fill('');expect(card.locator('.lot-card-cost-label')).to_have_count(1)
        card.locator('[data-simple-open]').click();page.locator('#simple-sale-tab').click();page.locator('#simple-amount').fill('500');page.locator('#simple-unit').select_option('bottle');page.locator('#simple-price').fill('1000');page.locator('#simple-save').click()
        expect(page.locator('#simple-current')).to_have_text('-137');page.locator('#simple-back').click();expect(card.locator('[data-summary-current]')).to_have_text('-137')
        current=page.evaluate('JSON.parse(localStorage.getItem("eb-v1"))');assert current['contacts']==fixture['contacts'] and current['documents']==fixture['documents']
        uncounted=copy.deepcopy(fixture);uncounted['inventoryOpenings']=[];page.evaluate('(d)=>localStorage.setItem("eb-v1",JSON.stringify(d))',uncounted);page.reload(wait_until='networkidle')
        expect(card.locator('[data-summary-current]')).to_have_text('Sin capturar');expect(card.locator('[data-summary-produced]')).to_have_text('438')
        assert page.evaluate('JSON.parse(localStorage.getItem("eb-v1"))')==uncounted
        assert not errors,errors
        print('PASS LOT CARD',width,'cost label above amount; produced vs initial vs live balance; sale/sample deductions; transfer conservation; discrepancies; signed stock; reload; no writes from viewing')
        ctx.close()
    browser.close()
