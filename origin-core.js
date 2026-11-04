'use strict';
/* Explicit origin assignment. Never initializes or relocates stock just by opening a lot. */
(function(root,factory){
  if(typeof module!=='undefined'&&module.exports)module.exports=factory;
  else root.EBLedger=factory(root.EBLedger);
})(typeof window==='undefined'?globalThis:window,function(I){
  const copy=x=>JSON.parse(JSON.stringify(x));
  function hasStockHistory(d,id){
    const l=(d.lots||[]).find(x=>x.id===id);
    if(l?.originInventoryInitialized||I.opening(d,id))return true;
    return ['lotShipments','lotSales','lotSampleActions','lotStockAdjustments','moves'].some(k=>(d[k]||[]).some(x=>x.lotId===id||x.lot===id));
  }
  function originLocations(d){return I.locations(d).filter(n=>I.locationInfo(d,n).kind==='warehouse');}
  function withOrigin(d,id,origin,day,stamp){
    const original=(d.lots||[]).find(x=>x.id===id);
    if(!original)throw Error('Guarda primero el lote.');
    origin=String(origin||'').trim();
    if(origin&&!originLocations(d).includes(origin))throw Error('Elige una bodega de origen registrada.');
    let next=copy(d);let l=next.lots.find(x=>x.id===id);l.originWarehouse=origin;
    // An existing count, even zero, or any recorded operation prevents a second receipt.
    if(!origin||hasStockHistory(d,id))return next;
    if(!Number.isSafeInteger(l.bottles)||l.bottles<1)throw Error('Completa la producción antes de registrar la bodega de origen.');
    next=I.saveOpening(next,id,{asOf:day,complete:true,rows:[{location:origin,tag:'Por clasificar',amount:l.bottles,unit:'bottle',isSample:false}],notes:'Alta de producción en bodega de origen. Las salidas se registran desde este saldo.',stamp},day);
    l=next.lots.find(x=>x.id===id);l.originInventoryInitialized=true;
    const o=I.opening(next,id);o.source='origin-production';o.originWarehouse=origin;
    I.balance(next,id);return next;
  }
  return {...I,originVersion:'1.0',hasStockHistory,originLocations,withOrigin};
});
