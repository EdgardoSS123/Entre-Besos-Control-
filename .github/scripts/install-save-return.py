from pathlib import Path
import re

def replace(path, old, new):
    p=Path(path);s=p.read_text()
    if new in s:return
    assert s.count(old)==1,(path,old[:110],s.count(old))
    p.write_text(s.replace(old,new,1))

# Load the small view-only helper before any authenticated UI module on every page.
replace('shared.js'," const scripts=[...document.querySelectorAll('script[type=\"application/x-eb-shared\"]')];", " const viewHelper=document.createElement('script');viewHelper.type='application/x-eb-shared';viewHelper.src='/edit-return.js?v=save-return1';document.head.append(viewHelper);\n const scripts=[viewHelper,...document.querySelectorAll('script[type=\"application/x-eb-shared\"]:not([src^=\"/edit-return.js\"])')];")
replace('simple-lot.js','window.EBSimpleUI={open};',"window.EBSimpleUI={open,context:()=>({id:active,tab:screen,from:preferred})};")
replace('commerce-ui.js','window.EBCommerceUI={render,stock,report};',"window.EBCommerceUI={render,stock,report,context:()=>({id:active,options:{stay:true,samples:by('samples-section')&&!by('samples-section').classList.contains('hidden'),from:by('sale-from')?.value}})};")
replace('commerce-ui.js',"&&!options.samples&&!options.shipmentId)return","&&!options.samples&&!options.shipmentId&&!options.stay)return")
# Defer repaint until the successful correction has closed. Errors leave the dialog and inputs intact.
replace('corrections-ui.js',"  function refresh(id){data=freshData();const found=data.lots.find(x=>x.id===id);if(found&&window.EBSimpleUI){window.EBSimpleUI.open(id);}else show('lots');}","  let correctionReturn=null,deferredLot=null;\n  function refresh(id){if(correctionReturn){deferredLot=id;return;}data=freshData();const found=data.lots.find(x=>x.id===id);if(found&&window.EBSimpleUI){window.EBSimpleUI.open(id);}else show('lots');}")
p=Path('corrections-ui.js');s=p.read_text();start=s.index('  function dialog(');end=s.index('\n  function stock(',start)
s=s[:start]+'''  function dialog(title,html,save,label='Guardar cambios',danger=false){
    const back=window.EBEditReturn?.capture(),d=document.createElement('dialog');let saving=false;
    d.className='eb-modal correction-modal';d.innerHTML='<h2>'+esc(title)+'</h2>'+html+'<p class="alert hidden" data-error role="alert"></p><div class="correction-footer"><button type="button" class="secondary" data-cancel>Cancelar</button><button type="button" class="'+(danger?'danger-button':'primary')+'" data-save>'+esc(label)+'</button></div>';
    document.body.append(d);d.onclose=()=>d.remove();d.querySelector('[data-cancel]').onclick=()=>{if(!saving)d.close();};
    d.querySelector('[data-save]').onclick=async()=>{
      if(saving)return;saving=true;const button=d.querySelector('[data-save]');button.disabled=true;button.textContent='Guardando…';d.querySelector('[data-error]').classList.add('hidden');
      correctionReturn=back||{};deferredLot=null;
      try{
        await save(d);const id=deferredLot;correctionReturn=null;deferredLot=null;
        window.EBEditReturn?.close(d);if(d.isConnected){d.close();d.remove();}window.EBShared?.cancelDraft?.();
        if(id)window.EBEditReturn.refresh(back,id);else window.EBEditReturn?.restore(back);
      }catch(e){const a=d.querySelector('[data-error]');a.textContent=e.message;a.classList.remove('hidden');a.scrollIntoView({block:'nearest'});}
      finally{correctionReturn=null;deferredLot=null;saving=false;button.disabled=false;button.textContent=label;}
    };d.showModal();return d;
  }''' +s[end:];p.write_text(s)
# Full lot editing returns to its original list or opened lot, including renamed lot IDs.
replace('control.js','function saveLot(){', 'let lotEditReturn=null;\nfunction saveLot(){')
replace('control.js',"function loadLot(id,copy){const l=data.lots.find(x=>x.id===id);if(!l)return;draft=", "function loadLot(id,copy){const l=data.lots.find(x=>x.id===id);if(!l)return;lotEditReturn=copy?null:window.EBEditReturn?.capture();draft=")
replace('control.js',"  draft=blank();loadedRevision=null;dirty=false;saveDraft();renderEditor();", "  lotEditReturn=null;draft=blank();loadedRevision=null;dirty=false;saveDraft();renderEditor();")
replace('control.js',"toast('Lote '+record.id+' guardado · '+number(r.n)+' botellas · '+cash(record.unitCost));renderLots();window.scrollTo(0,0);", "toast('Lote '+record.id+' guardado · '+number(r.n)+' botellas · '+cash(record.unitCost));if(lotEditReturn){const back=lotEditReturn;lotEditReturn=null;window.EBEditReturn.refresh(back,record.id);}else{renderLots();window.scrollTo(0,0);}window.EBShared?.cancelDraft?.();")
# Payment popup in the lot history follows the same return rule.
replace('simple-lot.js',"  function paymentDialog(id,saleId){\n    const s=", "  function paymentDialog(id,saleId){\n    const back=window.EBEditReturn?.capture();\n    const s=")
replace('simple-lot.js',"dialog.close();open(id,'sale');toast('Pago guardado; no cambia el inventario.');", "window.EBEditReturn.close(dialog);window.EBEditReturn.refresh(back,id);toast('Pago guardado; no cambia el inventario.');")
# Contacts: close inline editor and restore the country/search/position from before editing.
replace('office-ui.js',"function openForm(index){\n if(reader())return;", "let contactReturn=null;\nfunction openForm(index){\n if(reader())return;contactReturn=window.EBEditReturn?.capture();const previousCountry=selected;")
replace('office-ui.js',"localStorage.setItem('eb-v1',JSON.stringify(out));selected=$('contact-country').value;dirty=false;editing=null;renderContacts();message('Contacto guardado. Revisa «Actualizado» para confirmar la sincronización.');", "localStorage.setItem('eb-v1',JSON.stringify(out));selected=editing?previousCountry:$('contact-country').value;const back=contactReturn;dirty=false;editing=null;renderContacts();window.EBEditReturn?.restore(back);window.EBShared?.cancelDraft?.();message('Contacto guardado. Revisa «Actualizado» para confirmar la sincronización.');")
# Supplies / marketing: keep warehouse and search, and return to the edited card rather than an empty form.
replace('materials-ui.js',"  function edit(index) {\n    if(!discard())return;", "  let materialReturn=null;\n  function edit(index) {\n    if(!discard())return;materialReturn=window.EBEditReturn?.capture();")
replace('materials-ui.js',"editing=null;custom=false;changed=false;render();toast('Inventario guardado. Cantidad y costo total registrados.');", "const back=editing?materialReturn:null;editing=null;custom=false;changed=false;render();window.EBEditReturn?.restore(back);window.EBShared?.cancelDraft?.();materialReturn=null;toast('Inventario guardado. Cantidad y costo total registrados.');")
# Orders: retain partner, state/date filters, expanded history and scroll after modal save.
replace('orders-ui.js',"function openForm(id){\n if(!canEdit()||busy)return;", "let orderReturn=null;\nfunction openForm(id){\n if(!canEdit()||busy)return;orderReturn=window.EBEditReturn?.capture();")
replace('orders-ui.js'," if(dialog)dialog.close();render();", " const back=dialog?orderReturn:window.EBEditReturn?.capture();if(dialog)dialog.close();render();window.EBEditReturn?.restore(back);")
replace('orders-ui.js',"dirty=false;dialog.close();render();say('Sin cambios. No se volvió a descontar producto.');", "dirty=false;dialog.close();render();window.EBEditReturn?.restore(orderReturn);window.EBShared?.cancelDraft?.();say('Sin cambios. No se volvió a descontar producto.');")
# Document metadata: return to the current category/filter, after the server confirms the change.
replace('documents-ui.js',"function open(doc){\n if(!editor()||$('docs-dialog'))return;", "function open(doc){\n if(!editor()||$('docs-dialog'))return;const back=window.EBEditReturn?.capture();")
replace('documents-ui.js',"dirty=false;selected=input.category;trash=false;filter='';$('docs-status').value='';dialog.close();await load();message(", "dirty=false;if(!doc){selected=input.category;trash=false;filter='';$('docs-status').value='';}dialog.close();await load();window.EBEditReturn?.restore(back);message(")
# Helper is shipped as a static asset. No server/database or inventory logic changes.
p=Path('Dockerfile');s=p.read_text()
if 'COPY edit-return.js ' not in s:
 s=s.replace('COPY nginx.conf','COPY edit-return.js /usr/share/nginx/html/\nCOPY nginx.conf',1).replace('for asset in ','for asset in edit-return.js ',1)
p.write_text(s)
# Revalidate entrypoints for installed iPhone shortcuts without requiring data deletion.
for p in Path('.').glob('*.html'):
 s=p.read_text()
 for asset in ['shared.js','control.js','simple-lot.js','commerce-ui.js','corrections-ui.js','office-ui.js','materials-ui.js','orders-ui.js','documents-ui.js']:
  s=re.sub(re.escape(asset)+r'\?v=[^"\s]+',asset+'?v=save-return1',s)
 p.write_text(s)
print('Save/return UI integrated without changing business calculations or records.')
