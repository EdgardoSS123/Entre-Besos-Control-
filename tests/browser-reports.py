import os,json,shutil
from pathlib import Path
import pymupdf
from playwright.sync_api import sync_playwright,expect
from workspace_test import Workspace
workspace=Workspace()
BASE=workspace.base
OUT=Path('/tmp/eb-report-checks');OUT.mkdir(exist_ok=True,parents=True)
seed=json.loads(Path('/tmp/eb-report-fixture.json').read_text())

def check_pdf(path,required=(),excluded=(),min_pages=1):
    assert path.read_bytes().startswith(b'%PDF-'),path
    doc=pymupdf.open(path);assert len(doc)>=min_pages
    content=' '.join(' '.join(p.get_text() for p in doc).split())
    for term in required:assert term in content,(str(path),term,content[:500])
    for term in excluded:assert term not in content,(str(path),term)
    for i,page in enumerate(doc):
        assert page.get_images(),('Missing logo',str(path),i)
        assert 'SAGAV CUATRO' in page.get_text() and f'Página {i+1} de {len(doc)}' in page.get_text()
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                for span in line['spans']:
                    x0,y0,x1,y1=span['bbox']
                    assert x0>=33 and x1<=580 and y0>=12 and y1<=780,(path.name,i,span['text'],span['bbox'])
    print('PASS PDF',path.name,len(doc),'pages',flush=True)

def download(page,name):
    before=page.evaluate('localStorage.getItem("eb-v1")')
    with page.expect_download(timeout=60000) as event:
        result=page.evaluate('async()=>!!(await window.EBReports.download(window.EBReports.context()))')
        assert result,page.locator('#eb-pdf-status').inner_text()
    event.value.save_as(OUT/name)
    assert event.value.suggested_filename.endswith('.pdf')
    expect(page.locator('#eb-report-pdf')).to_be_enabled()
    assert before==page.evaluate('localStorage.getItem("eb-v1")')
    page.locator('#eb-pdf-ready button').filter(has_text='Volver a la app').click()
    return OUT/name

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),headless=True,args=['--no-sandbox'])
    for width in (1440,390):
        ctx=workspace.context(browser,viewport={'width':width,'height':980},accept_downloads=True)
        page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.accept())
        workspace.goto(page,BASE+'materials.html?kind=supplies',wait_until='load');page.evaluate('(d)=>localStorage.setItem("eb-v1",JSON.stringify(d))',seed);workspace.reload(page)
        page.locator('#material-name').select_option(label='Otros');expect(page.locator('#material-custom-name')).to_be_visible();expect(page.locator('#material-custom-name')).to_have_value('')
        page.locator('#material-location').select_option('CDMX');page.locator('#material-qty').fill('12');page.locator('#material-cost').fill('600')
        before=page.evaluate('localStorage.getItem("eb-v1")');page.locator('#material-save').click();assert before==page.evaluate('localStorage.getItem("eb-v1")')
        page.locator('#material-custom-name').fill('Separadores especiales');expect(page.locator('#material-unit')).to_have_text('$50.00')
        page.locator('#material-name').select_option('Tapones');expect(page.locator('#material-custom-name')).to_be_hidden();expect(page.locator('#material-qty')).to_have_value('12')
        page.locator('#material-name').select_option(label='Otros');expect(page.locator('#material-custom-name')).to_have_value('Separadores especiales');page.locator('#material-save').click()
        workspace.reload(page);assert 'Separadores especiales' in page.locator('#material-name').inner_text();expect(page.locator('[data-record="1"]')).to_contain_text('$600.00')
        page.locator('[data-edit-material="1"]').click();page.locator('#material-name').select_option(label='Otros');page.locator('#material-custom-name').fill('Separadores nuevos');page.locator('#material-save').click();expect(page.locator('[data-record="1"]')).to_contain_text('Separadores nuevos')
        page.locator('#material-filter').select_option('CDMX');path=download(page,f'insumos-{width}.pdf');check_pdf(path,['Separadores nuevos','CDMX','$600.00','$50.00'],['Botellas vacías'])
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.screenshot(path=str(OUT/f'insumos-{width}.png'),full_page=True)
        page.locator('[data-kind="marketing"]:visible').first.click();path=download(page,f'marketing-{width}.pdf');check_pdf(path,['Playeras','Sin capturar','Material histórico sin precio'])
        workspace.goto(page,BASE,wait_until='load');path=download(page,f'general-{width}.pdf');check_pdf(path,['PRUEBA-PDF','714','683','CLIENTE DE PRUEBA','Separadores nuevos'])
        page.evaluate("window.EBOperations.renderStock('PRUEBA-PDF')");expect(page.locator('#simple-print')).to_have_text('PDF');path=download(page,f'lote-{width}.pdf');check_pdf(path,['PRUEBA-PDF','683','Muestras','CLIENTE DE PRUEBA'])
        page.locator('#nav-warehouses' if width>950 else '#mobile-warehouses').click();page.locator('#warehouse-filter').select_option('CDMX');path=download(page,f'bodega-{width}.pdf');check_pdf(path,['Inventario por bodega','623','CDMX'])
        assert not errors,errors
        ctx.close()
    ctx=workspace.context(browser,accept_downloads=True);page=ctx.new_page();workspace.goto(page,BASE+'materials.html?kind=marketing',wait_until='load')
    long=json.loads(json.dumps(seed));long['materials']=[{'name':f'Objeto {i:03d} · Menús, exhibidores y materiales para socios','presentation':'Edición especial para eventos y degustaciones','qty':i+1,'totalCost':(i+1)*150,'loc':'CDMX','currency':'MXN'} for i in range(80)]
    page.evaluate('(d)=>localStorage.setItem("eb-v1",JSON.stringify(d))',long);workspace.reload(page);path=download(page,'marketing-multipagina.pdf');check_pdf(path,['Objeto 000','Objeto 079','Menús'],min_pages=3)
    failctx=workspace.context(browser,accept_downloads=True);failpage=failctx.new_page();failpage.route('**/EB%20logo.jpg',lambda route:route.abort());workspace.goto(failpage,BASE+'materials.html?kind=marketing',wait_until='load')
    failpage.locator('#eb-report-pdf').click();expect(failpage.locator('#eb-pdf-status')).to_contain_text('No se generó',timeout=15000)
    failctx.close();ctx.close();browser.close()
print('PASS Others, PDF download, filtering, missing-cost handling, embedded logo on every page, pagination and immutable records.',flush=True)
