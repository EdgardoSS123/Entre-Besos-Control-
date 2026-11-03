"""Isolated browser storage only: never writes into a user's browser or backend."""
import os, shutil, subprocess, sys, json
from playwright.sync_api import sync_playwright
BASE=os.environ.get('EB_TEST_URL','https://entre-besos-web-production.up.railway.app/')
chrome=shutil.which('google-chrome') or shutil.which('chromium')
if not chrome: subprocess.run([sys.executable,'-m','playwright','install','--with-deps','chromium'],check=True)
with sync_playwright() as p:
    options={'headless':True, 'args':['--no-sandbox']}
    if chrome: options['executable_path']=chrome
    browser=p.chromium.launch(**options)
    for width,height in [(1440,1000),(390,844),(375,812)]:
        context=browser.new_context(viewport={'width':width,'height':height},is_mobile=width<700,has_touch=width<700)
        page=context.new_page(); errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(BASE+'?check=litros32',wait_until='networkidle')
        page.locator('#lot-id').wait_for()
        assert page.evaluate('EBCosts.version')=='eb-costos-3.2'
        page.wait_for_function('Array.from(document.images).every(i=>i.complete && i.naturalWidth>0)')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Horizontal overflow'
        assert page.locator('main input').first.get_attribute('id')=='lot-id'
        assert page.locator('.cost-table tbody tr').count()==14
        assert page.locator('#bottles').get_attribute('readonly') is not None
        page.locator('#lot-id').fill('CI-LITROS-01')
        page.locator('#producedLiters').fill('432')
        page.locator('#lossLiters').fill('0')
        page.locator('#liquid').fill('200')
        for i,v in enumerate([20,5,3,4,2,1,60,1,600,1200,600,1800,300]):page.locator('#amount-'+str(i)).fill(str(v))
        assert page.locator('#bottles').input_value()=='600'
        assert page.locator('#liquid-converted').inner_text()=='$144.00'
        assert page.locator('#unit-total').inner_text()=='$197.50'
        assert page.locator('#total-result').inner_text()=='$118,500.00'
        if width>700:
            page.locator('#pin-summary').click()
            assert page.locator('.summary').evaluate('(el)=>getComputedStyle(el).position')=='static'
            page.locator('#pin-summary').click()
        save='#mobile-save-button' if width<700 else '#save-lot'
        page.locator(save).click()
        assert page.locator('.saved-lot').count()==1
        page.reload();page.locator('#lot-id').wait_for()
        assert page.locator('#producedLiters').input_value()=='432'
        assert page.locator('#bottles').input_value()=='600'
        page.locator('#show-lots').click();page.locator('[data-copy]').click()
        page.locator('#lot-id').fill('CI-LITROS-02')
        page.locator('#producedLiters').fill('500');page.locator('#lossLiters').fill('10')
        assert page.locator('#bottles').input_value()=='680'
        assert page.locator('#remaining-liters').inner_text()=='0.4 L'
        assert page.locator('#net-liters').inner_text()=='490 L'
        page.locator(save).click()
        stored=page.evaluate("JSON.parse(localStorage.getItem('eb-v1'))")
        assert stored['lots'][0]['unitCost']==197.5
        assert stored['lots'][1]['remainingLiters']==.4
        assert stored['lots'][1]['lossLiters']==10
        assert stored['lots'][1]['bottles']==680
        assert stored['lots'][1]['materialsStatus']=='requirements_only'
        assert next(m['quantity'] for m in stored['lots'][1]['materialsPlan'] if m['name']=='Corrugados')==114
        assert stored['moves']==[], 'Costing must not post inventory movements'
        secondCost=stored['lots'][1]['unitCost']
        page.locator('[data-edit="CI-LITROS-01"]').click();page.locator('#amount-0').fill('21');page.locator(save).click()
        assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).lots.map(x=>x.unitCost)")==[198.5,secondCost]
        assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).lotRevisions[0].record.unitCost")==197.5
        page.evaluate('window.print=()=>{}');page.locator('[data-print="CI-LITROS-02"]').click()
        assert 'Sobrante: 0.4 L' in page.locator('#print-view').inner_text()
        page.locator('[data-copy="CI-LITROS-02"]').click();page.locator('#lot-id').fill('INVALID-LOSS');page.locator('#lossLiters').fill('501');page.locator(save).click()
        assert 'merma no puede ser mayor' in page.locator('#form-errors').inner_text()
        assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).lots.length")==2
        assert not errors, errors
        print('PASS BROWSER',width,': liters, loss, readonly bottles, remainder, costs, materials, save, reload, edit history, print, invalid loss and unchanged inventory')
        context.close()
    old={'lots':[{'id':'OLD-01','p':0,'date':'2026-11-01','ml':720,'bottles':600,'liters':440,'liquid':200,'includeLoss':True,'costingVersion':3,'unitCost':200.16666666666666,'totalCost':120100}], 'moves':[], 'contacts':[], 'costs':{},'expenses':[{'note':'keep-me'}]}
    ctx=browser.new_context();page=ctx.new_page()
    page.add_init_script('localStorage.setItem("eb-v1",'+json.dumps(json.dumps(old))+');')
    page.goto(BASE+'?check=migration32',wait_until='networkidle');page.locator('#show-lots').click();page.locator('[data-edit="OLD-01"]').click()
    assert page.locator('#producedLiters').input_value()=='440'
    assert page.locator('#lossLiters').input_value()=='8'
    assert page.locator('#bottles').input_value()=='600'
    assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1'))")==old
    print('PASS: historical lot and unrelated data unchanged on reading and editing preview')
    ctx.close();browser.close()
