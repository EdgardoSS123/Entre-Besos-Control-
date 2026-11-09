/* View state only. Never writes business data or infers whether a save succeeded. */
(function(){
'use strict';
const root=()=>document.querySelector('#app,#materials-app,#office-app,#orders-app,#documents-app');
const filters=['search-lots','warehouse-filter','history-warehouse','material-search','material-filter','contact-search','docs-search','docs-status','orders-filter-from','orders-filter-to'];
const attrs=['data-record-edit','data-stock-edit','data-edit-material','data-contact-edit','data-edit-doc','data-edit-order','data-edit','data-kind','data-payment-id'];
function selector(el){
 if(!el||el===document.body)return'';
 if(el.id)return'#'+CSS.escape(el.id);
 const parts=attrs.filter(a=>el.hasAttribute(a)).map(a=>'['+a+'='+JSON.stringify(el.getAttribute(a))+']');
 return parts.length?el.tagName.toLowerCase()+parts.join(''):'';
}
function details(host){
 const seen=new Map();return[...host.querySelectorAll('details')].map(el=>{
  const article=el.closest('article'),button=article?.querySelector('[data-record-edit],[data-edit],[data-edit-doc],[data-edit-order]');
  const base=el.id?'#'+el.id:[selector(button),el.className,el.querySelector(':scope > summary')?.textContent.trim()].join('|');
  const n=seen.get(base)||0;seen.set(base,n+1);return{key:base+'|'+n,open:el.open,el};
 });
}
function capture(){
 const host=root();if(!host)return null;
 let scope='page',context=null;
 if(document.getElementById('simple-produced')){scope='simple';context=window.EBSimpleUI?.context?.();}
 else if(document.getElementById('sale-panel')){scope='commerce';context=window.EBCommerceUI?.context?.();}
 else if(document.getElementById('warehouse-filter'))scope='warehouses';
 else if(document.getElementById('saved-list'))scope='lots';
 return{host:host.id,path:location.pathname,scope,context,x:scrollX,y:scrollY,
  focus:selector(document.activeElement),
  filters:filters.map(id=>document.getElementById(id)).filter(el=>el&&host.contains(el)).map(el=>({id,value:el.value})),
  details:details(host).map(({key,open})=>({key,open}))};
}
function restore(state){
 if(!state||location.pathname!==state.path)return;
 let host=document.getElementById(state.host);if(!host)return;
 for(const f of state.filters){const el=document.getElementById(f.id);if(!el||!host.contains(el)||el.value===f.value)continue;
  if(el.tagName==='SELECT'&&![...el.options].some(o=>o.value===f.value))continue;
  el.value=f.value;el.dispatchEvent(new Event(el.tagName==='SELECT'||el.type==='date'?'change':'input',{bubbles:true}));
 }
 host=document.getElementById(state.host);if(!host)return;
 const saved=new Map(state.details.map(x=>[x.key,x.open]));for(const d of details(host))if(saved.has(d.key))d.el.open=saved.get(d.key);
 const move=()=>{if(location.pathname!==state.path)return;const el=state.focus?document.querySelector(state.focus):null;if(el&&host.contains(el))el.focus({preventScroll:true});window.scrollTo({left:state.x,top:state.y,behavior:'instant'});};
 move();requestAnimationFrame(()=>requestAnimationFrame(move));
}
function refresh(state,lotId){
 if(state?.scope==='simple'&&window.EBSimpleUI){const c=state.context||{};window.EBSimpleUI.open(lotId||c.id,c.tab||'count',c.from);}
 else if(state?.scope==='commerce'&&window.EBCommerceUI){const c=state.context||{};window.EBCommerceUI.render(lotId||c.id,c.options||{});}
 else if(state?.scope==='warehouses')window.EBOperations?.renderWarehouses();
 else if(state?.scope==='lots')window.renderLots?.();
 else if(lotId&&window.EBSimpleUI)window.EBSimpleUI.open(lotId);
 restore(state);
}
function close(dialog){
 if(!dialog)return;const focused=document.activeElement;if(focused&&dialog.contains(focused))focused.blur();
 if(dialog.open)dialog.close();dialog.remove();
}
window.EBEditReturn={capture,restore,refresh,close};
})();
