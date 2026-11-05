/* Installation helpers only. No automatic migration, upload or overwrite. */
(function(root){
  'use strict';
  const KEY='eb-v1', DRAFT='eb-cost-draft-v3';
  function parse(raw){
    if(typeof raw!=='string'||raw.length>10*1024*1024)throw Error('Selecciona un respaldo JSON de Entre Besos de hasta 10 MB.');
    const d=JSON.parse(raw,(k,v)=>{if(['__proto__','prototype','constructor'].includes(k))throw Error('El archivo contiene campos no admitidos.');return v;});
    if(!d||typeof d!=='object'||Array.isArray(d)||!Array.isArray(d.lots)||!Array.isArray(d.moves))throw Error('No es un respaldo de Entre Besos Control. Usa el archivo del botón Respaldo.');
    for(const k of ['lots','moves','contacts','inventoryOpenings','lotSales','lotShipments','lotSampleActions','lotStockAdjustments','materials','supplies','materialInventoryHistory']){
      if(d[k]!==undefined&&(!Array.isArray(d[k])||d[k].some(v=>!v||typeof v!=='object'||Array.isArray(v))))throw Error('El apartado '+k+' no tiene el formato esperado.');
    }
    const ids=new Set();for(const l of d.lots){if(!['string','number'].includes(typeof l.id)||!String(l.id).trim()||ids.has(String(l.id)))throw Error('El respaldo tiene lotes sin código o repetidos.');ids.add(String(l.id));}
    return d;
  }
  function meaningful(v){
    if(v===null||v===undefined||v===false||v===0||v==='')return false;
    if(Array.isArray(v))return v.length>0;
    if(typeof v==='object')return Object.values(v).some(meaningful);
    return true;
  }
  function hasDraft(raw){
    if(!raw)return false;const d=JSON.parse(raw);
    if(!d||typeof d!=='object')return true;
    return !!(d.id||d.editId||[d.producedLiters,d.liquid].some(v=>v!==''&&v!==null&&v!==undefined)||(Array.isArray(d.lines)&&d.lines.some(x=>Number(x.amount)!==0)));
  }
  function inspect(storage){
    const raw=storage.getItem(KEY),draft=storage.getItem(DRAFT);
    return{raw,draft,occupied:!!(raw&&meaningful(parse(raw)))||hasDraft(draft)};
  }
  function restore(storage,raw,expected){
    const d=parse(raw),now=inspect(storage);
    if(now.occupied)throw Error('Este dispositivo ya tiene datos o una captura pendiente. No se sobrescribió nada. Conserva ambos respaldos para conciliarlos.');
    if(now.raw!==expected.raw||now.draft!==expected.draft)throw Error('Los datos cambiaron mientras elegías el archivo. Vuelve a abrir la recuperación.');
    storage.setItem(KEY,raw);return d;
  }
  const api={parse,inspect,restore,KEY,DRAFT};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.EBDeviceBackup=api;
})(typeof window==='undefined'?globalThis:window);
