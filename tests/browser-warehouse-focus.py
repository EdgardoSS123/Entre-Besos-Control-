"""Read-only UI checks using synthetic data in isolated browser profiles."""
import os,shutil,json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from workspace_test import Workspace
workspace=Workspace()
URL=workspace.base
OUT=Path('/tmp/eb-warehouse-focus');OUT.mkdir(exist_ok=True)
PLACES=['Oaxaca','CDMX','USA','Singapur','EB1-1 · Edgardo','EB1-2 · Ricardo','EB1-3 · Mario']
COUNTS=[72,60,48,12,18,24,30]
fixture={'lots':[{'id':'CI-WAREHOUSE-FOCUS','p':0,'date':'2026-11-01','ml':720,'bottles':600,'unitCost':200,'totalCost':120000}], 'moves':[], 'contacts':[], 'costs':{}, 'inventoryOpenings':[{'lotId':'CI-WAREHOUSE-FOCUS','asOf':'2026-11-01','complete':True,'rows':[{'location':place,'tag':'Nacional','quantity':n,'sampleQuantity':0} for place,n in zip(PLACES,COUNTS)]}]}
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),headless=True,args=['--no-sandbox'])
    for width,height in [(1440,1000),(390,844),(375,812)]:
        ctx=workspace.context(browser,viewport={'width':width,'height':height},is_mobile=width<700,has_touch=width<700)
        page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        workspace.goto(page,URL,wait_until='networkidle')
        page.evaluate('(data)=>localStorage.setItem("eb-v1",JSON.stringify(data))',fixture)
        before=page.evaluate('localStorage.getItem("eb-v1")')
        page.locator('#nav-warehouses' if width>950 else '#mobile-warehouses').click()
        for place,n in zip(PLACES,COUNTS):
            page.locator('#warehouse-filter').select_option(place)
            expect(page.locator('#warehouse-filter')).to_have_value(place)
            assert page.locator('.partner-depots,[data-partner-location]').count()==0
            expect(page.locator('.warehouse-card')).to_have_count(1)
            expect(page.locator('.warehouse-card > strong')).to_have_text(str(n))
            expect(page.locator('.warehouse-card > small')).to_have_text('botellas en '+place)
            assert all(x in page.locator('#warehouse-filter option').all_text_contents() for x in PLACES)
            assert page.evaluate('localStorage.getItem("eb-v1")')==before
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Horizontal overflow'
        page.locator('#warehouse-filter').select_option('Oaxaca')
        page.screenshot(path=str(OUT/f'warehouse-oaxaca-{width}.png'),full_page=True)
        workspace.reload(page,wait_until='networkidle')
        assert page.evaluate('localStorage.getItem("eb-v1")')==before
        assert not errors,errors
        print('PASS WAREHOUSE FOCUS',width,'selected location only; all 7 locations accessible; no repeated CDMX panel; no writes; reload and responsive layout')
        ctx.close()
    browser.close()
