import os,json,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
import pymupdf
BASE=os.environ.get('EB_TEST_URL','http://127.0.0.1:8765/').rstrip('/')+'/'
OUT=Path('/tmp/eb-app-checks');OUT.mkdir(exist_ok=True,parents=True)
seed=json.loads(Path('/tmp/eb-app-fixture.json').read_text())

def restore_file(page):
 page.locator('.eb-app-recovery').evaluate('(e)=>e.open=true')
 page.locator('#eb-backup-file').set_input_files({'name':'respaldo.json','mimeType':'application/json','buffer':json.dumps(seed).encode()})

with sync_playwright() as p:
 for engine,width in [('chromium',1440),('chromium',390),('webkit',390)]:
  launcher=getattr(p,engine)
  browser=launcher.launch(headless=True,**({'executable_path':shutil.which('google-chrome') or shutil.which('chromium'),'args':['--no-sandbox']} if engine=='chromium' else {}))
  options={'viewport':{'width':width,'height':900},'accept_downloads':True}
  if width==390:options.update({'is_mobile':True,'has_touch':True,'device_scale_factor':2,'user_agent':'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'})
  ctx=browser.new_context(**options);page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE+'instalar.html',wait_until='load')
  expect(page.locator('link[rel="manifest"]')).to_have_attribute('href','/app.webmanifest')
  expect(page.locator('meta[name="apple-mobile-web-app-title"]')).to_have_attribute('content','Entre Besos')
  manifest=page.request.get(BASE+'app.webmanifest').json();assert manifest['display']=='standalone' and manifest['start_url']=='/'
  icon=page.request.get(BASE+'icons/eb-180.png');assert icon.ok and icon.body().startswith(b'\x89PNG')
  assert page.evaluate('localStorage.getItem("eb-v1")') is None
  page.locator('#eb-install-action').click();expect(page.locator('#eb-install-guide')).to_be_visible()
  page.evaluate('Object.defineProperty(navigator,"share",{configurable:true,value:async (d)=>{window.__share=d;}})')
  page.locator('#eb-share-action').click();page.wait_for_function('window.__share !== undefined')
  payload=page.evaluate('window.__share');assert payload['url']==BASE+'instalar.html' and set(payload)=={'title','text','url'}
  page.evaluate('Object.defineProperty(navigator,"share",{configurable:true,value:undefined}); Object.defineProperty(navigator,"clipboard",{configurable:true,value:{writeText:async(v)=>{window.__copied=v;}}});')
  page.locator('#eb-share-action').click();page.wait_for_function('window.__copied !== undefined');assert page.evaluate('window.__copied')==BASE+'instalar.html'
  page.screenshot(path=str(OUT/f'install-{engine}-{width}.png'),full_page=True)
  restore_file(page);expect(page.locator('#eb-restore-preview')).to_be_visible();assert page.evaluate('localStorage.getItem("eb-v1")') is None
  page.locator('#eb-restore-confirm').click();page.wait_for_url(BASE);expect(page.locator('[data-summary-current]')).to_have_text('834')
  expect(page.locator('[data-summary="current"]')).to_contain_text('1 pallet + 59 cajas + 0 botellas sueltas')
  assert page.evaluate('JSON.parse(localStorage.getItem("eb-v1"))')==seed
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
  page.screenshot(path=str(OUT/f'lots-{engine}-{width}.png'),full_page=True)
  page.locator('#eb-app-menu').click();expect(page.locator('#eb-install-sheet')).to_be_visible();restore_file(page);expect(page.locator('#eb-app-status')).to_contain_text('ya tiene datos');assert page.locator('#eb-restore-preview').is_hidden();page.locator('.eb-app-close').click()
  page.get_by_role('button',name='Abrir lote',exact=True).click();expect(page.locator('#simple-current')).to_have_text('834');expect(page.locator('.simple-location')).to_contain_text('1 pallet + 59 cajas + 0 botellas sueltas')
  page.screenshot(path=str(OUT/f'lot-{engine}-{width}.png'),full_page=True)
  page.locator('#mobile-warehouses' if width==390 else '#nav-warehouses').click();page.locator('#warehouse-filter').select_option('Oaxaca');expect(page.locator('.warehouse-card')).to_contain_text('1 pallet + 59 cajas + 0 botellas sueltas')
  page.screenshot(path=str(OUT/f'warehouse-{engine}-{width}.png'),full_page=True)
  with page.expect_download() as event:page.locator('#eb-report-pdf').click()
  pdf=OUT/f'warehouse-{engine}-{width}.pdf';event.value.save_as(pdf)
  doc=pymupdf.open(pdf);text=' '.join(' '.join(x.get_text().split()) for x in doc);assert '834' in text and '1 pallet + 59 cajas + 0 sueltas' in text
  for i,pg in enumerate(doc):
   assert pg.get_images();pg.get_pixmap(matrix=pymupdf.Matrix(1.4,1.4)).save(OUT/f'pdf-{engine}-{width}-{i}.png')
   for b in pg.get_text('dict')['blocks']:
    for line in b.get('lines',[]):
     for span in line['spans']:
      x0,y0,x1,y1=span['bbox'];assert x0>=30 and x1<=585 and y0>=10 and y1<=780,(span['text'],span['bbox'])
  page.goto(BASE+'materials.html?kind=supplies',wait_until='load');page.locator('#eb-app-menu').click();expect(page.locator('#eb-install-sheet')).to_be_visible();page.locator('.eb-app-close').click();assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
  assert page.evaluate('JSON.parse(localStorage.getItem("eb-v1"))')==seed;assert not errors,errors
  ctx.close()
  # Standalone display is emulated, not a claim of installing on a physical iPhone.
  ctx=browser.new_context(**options);ctx.add_init_script('Object.defineProperty(navigator,"standalone",{value:true})');page=ctx.new_page();page.goto(BASE+'instalar.html');expect(page.locator('#eb-install-action')).to_be_hidden();expect(page.locator('#eb-install-state')).to_contain_text('como app');ctx.close();browser.close()
  print('PASS APP',engine,width,'manifest/icon/share/restore/packaging/pdf/preservation',flush=True)
