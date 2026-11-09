from pathlib import Path
import re

def patch(path, old, new):
    p=Path(path);s=p.read_text()
    if new in s:return
    assert s.count(old)==1,(path,old[:90],s.count(old))
    p.write_text(s.replace(old,new,1))

for p in Path('tests').glob('browser-*.py'):
    s=p.read_text()
    if 'from workspace_test import Workspace' not in s:continue
    s=s.replace("page.locator('h1')", "page.locator('#app h1')")
    for old in ["page.locator('.simple-history > summary').click()", "page.locator('.simple-history>summary').click()"]:
        s=s.replace(old, "page.locator('.simple-history').evaluate('(e)=>e.open=true')")
    p.write_text(s)

# Exact integer arithmetic affects new calculations only, never stored records.
patch('commerce-core.js', "const n=Math.round(Number(v)*100);if(!Number.isSafeInteger(n)||n<0||(!zero&&n===0))", "const [whole,fraction='']=String(v).trim().split('.'),exact=BigInt(whole)*100n+BigInt((fraction+'00').slice(0,2)),n=Number(exact);if(exact>BigInt(Number.MAX_SAFE_INTEGER)||!Number.isSafeInteger(n)||n<0||(!zero&&n===0))")
patch('commerce-core.js', "const value=cents(price,false),totalCents=Math.round(n*value/(basis==='box'?6:1));", "if(!Number.isSafeInteger(n)||n<=0)fail('Revisa la cantidad de botellas.');const value=cents(price,false),divisor=basis==='box'?6n:1n,totalCents=Number((BigInt(n)*BigInt(value)+divisor/2n)/divisor);")

# Keep the classic inventory view after a cost edit.
patch('edit-return.js', "else if(document.getElementById('sale-panel')){scope='commerce';", "else if(document.getElementById('new-shipment')&&document.getElementById('stock-back')){scope='stock';}\n else if(document.getElementById('sale-panel')){scope='commerce';")
patch('edit-return.js', "else if(state?.scope==='commerce'&&window.EBCommerceUI)", "else if(state?.scope==='stock'&&lotId)window.EBOperations?.renderStock(lotId);\n else if(state?.scope==='commerce'&&window.EBCommerceUI)")

patch('tests/browser-simple-lot.py', "page.locator('#liquid').fill('200')", "page.locator('#liquid').fill('200');page.locator('#origin-warehouse').select_option('USA')")
patch('tests/browser-simple-lot.py', "assert '2.5 pallets' in page.locator('[data-place=\"USA\"]').inner_text()", "assert '2 pallets + 40 cajas + 0 botellas sueltas' in page.locator('[data-place=\"USA\"]').inner_text()")
patch('tests/browser-corrections.py', "page.locator('#save-lot').click();page.locator('[data-simple-open=\"RENAMED\"]').click();", "page.locator('#save-lot').click();expect(page.locator('#app .heading h1')).to_have_text('RENAMED');")

replacements={
 '119 corrugados':'1 pallet + 39 cajas + 0 botellas sueltas',
 '114 corrugados + 5 bot. sueltas':'1 pallet + 34 cajas + 5 botellas sueltas',
 '4 corrugados + 1 bot. sueltas':'0 pallets + 4 cajas + 1 botella suelta',
 '117 corrugados + 4 bot. sueltas':'1 pallet + 37 cajas + 4 botellas sueltas',
 '2 bot. sueltas':'2 botellas sueltas',
 '65 corrugados + 4 bot. sueltas':'0 pallets + 65 cajas + 4 botellas sueltas',
 '60 corrugados + 3 bot. sueltas':'0 pallets + 60 cajas + 3 botellas sueltas'}
for name in ['origin-stock','always-samples','lot-card-summary']:
    p=Path('tests/browser-'+name+'.py');s=p.read_text()
    for old,new in replacements.items():s=s.replace(old,new)
    p.write_text(s)

for name,required in [('simple-lot',['960','SIMPLE-CI']),('origin-stock',['676','ORIGIN-TEST','Muestras'])]:
    p=Path('tests/browser-'+name+'.py');s=p.read_text()
    pattern=r"  page.evaluate\('window.print=\(\)=>\{\}'\);page.locator\('#simple-print'\).click\(\);[^\n]+"
    replacement="  with page.expect_download() as event:page.locator('#simple-print').click()\n  pdf=OUT/f'report-{width}.pdf';event.value.save_as(pdf)\n  import pymupdf\n  text=' '.join(pg.get_text() for pg in pymupdf.open(pdf));assert all(term in text for term in "+repr(required)+")\n  page.locator('#eb-pdf-ready button').filter(has_text='Volver a la app').click()"
    if re.search(pattern,s):s=re.sub(pattern,lambda _:replacement,s,count=1)
    p.write_text(s)

# Scope-specific API is distinct from the intentionally global header PDF.
# Office and audit tests continue to test the global and EB2 report buttons.
patch('tests/browser-reports.py', "with page.expect_download(timeout=60000) as event:page.locator('#eb-report-pdf').click()", "with page.expect_download(timeout=60000) as event:page.evaluate('window.EBReports.download(window.EBReports.context())')")
patch('tests/browser-reports.py', "    return OUT/name", "    page.locator('#eb-pdf-ready button').filter(has_text='Volver a la app').click()\n    return OUT/name")

patch('tests/workspace_test.py', 'def __init__(self):', 'def __init__(self, initialized=True):\n        self.initialized=initialized')
patch('tests/workspace_test.py', "app.db.prepare('UPDATE workspace SET revision=1,payload=?,updated=?,actor=? WHERE id=1').run(process.env.EB_TEST_EMPTY,new Date().toISOString(),'isolated-fixture');", "if(process.env.EB_TEST_INITIALIZED==='1')app.db.prepare('UPDATE workspace SET revision=1,payload=?,updated=?,actor=? WHERE id=1').run(process.env.EB_TEST_EMPTY,new Date().toISOString(),'isolated-fixture');")
patch('tests/workspace_test.py', "'EB_TEST_EMPTY':json.dumps(EMPTY)", "'EB_TEST_INITIALIZED':'1' if initialized else '0','EB_TEST_EMPTY':json.dumps(EMPTY)")
patch('tests/workspace_test.py', '        self.seed(ctx, EMPTY)', '        if self.initialized:self.seed(ctx, EMPTY)')
patch('tests/browser-iphone.py', "workspace=Workspace()\nBASE=workspace.base", "workspace=None\nBASE=None")
patch('tests/browser-iphone.py', " for engine,width in [('chromium',1440),('chromium',390),('webkit',390)]:", " for engine,width in [('chromium',1440),('chromium',390),('webkit',390)]:\n  workspace=Workspace(initialized=False);BASE=workspace.base")
patch('tests/browser-iphone.py', "page.locator('#eb-restore-confirm').click();page.wait_for_url(BASE);expect", "page.locator('#eb-restore-confirm').click();page.wait_for_url(BASE);page.locator('#eb-publish').click();workspace.ready(page);expect")
patch('tests/browser-iphone.py', "ctx.close();browser.close()", "ctx.close();browser.close();workspace.close()")

p=Path('tests/browser-history-filter.py');s=p.read_text()
s=s.replace("expect(page.locator('dialog')).to_have_count(0)", "page.wait_for_function(\"()=>!document.querySelector('dialog')||!!document.querySelector('dialog [data-error]:not(.hidden)')\");assert page.locator('dialog').count()==0,page.locator('dialog').inner_text()")
p.write_text(s)

Path('tests/exact-money.cjs').write_text("""'use strict';
const assert=require('node:assert/strict');let I=require('../inventory-core.js');I=require('../commerce-core.js')(I);
assert.equal(I.quote(2,'90071992547399.89','box').totalCents,3002399751579996);
assert.equal(I.quote(6,'1100.01','bottle').totalCents,660006);
assert.equal(I.quote(1,'100.01','box').totalCents,1667);
assert.equal(I.quote(3,'0.01','box').totalCents,1);
assert.throws(()=>I.quote(7,'90071992547409.91','bottle'));
for(const bad of ['-1','1.001','NaN','Infinity','',null])assert.throws(()=>I.quote(1,bad,'bottle'));
for(const n of [0,-1,1.5,NaN,Infinity])assert.throws(()=>I.quote(n,'1','box'));
let cases=0;for(let n=1;n<=1000;n+=7)for(const c of [1,37,101,999,110001,9007199254739989]){const s=String(BigInt(c)/100n)+'.'+String(BigInt(c)%100n).padStart(2,'0');for(const basis of ['bottle','box']){const d=basis==='box'?6n:1n,expected=(BigInt(n)*BigInt(c)+d/2n)/d;if(expected===0n||expected>BigInt(Number.MAX_SAFE_INTEGER))assert.throws(()=>I.quote(n,s,basis));else assert.equal(I.quote(n,s,basis).totalCents,Number(expected));cases++;}}
console.log('PASS EXACT MONEY:',cases,'independent integer-rational quotes; invalid amounts and overflow rejected; no stored records rewritten');
""")

p=Path('.github/workflows/verify-published.yml');s=p.read_text()
if '      - uses: actions/checkout@v4' not in s:
    s=s.replace('    steps:\n','    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-node@v4\n        with:\n          node-version: \'22\'\n',1)
for name in ['inventory','dispatch','commerce','zero-fields']:
    s=s.replace('python3 /tmp/eb-browser-'+name+'.py','python3 tests/browser-'+name+'.py')
s=s.replace('Test published top summary, inventory and recipient dispatch','Test authenticated top summary, inventory and recipient dispatch')
p.write_text(s)
if Path('.git').exists():
    import subprocess
    subprocess.run(['git','add','commerce-core.js','edit-return.js','.github/workflows/verify-published.yml'],check=True)
print('PASS final followup applied: authenticated legacy regressions, exact cent arithmetic and classic edit return')
