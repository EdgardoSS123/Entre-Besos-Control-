'use strict';
const path=require('node:path');
function inspect(data,root){
 let I=require(path.join(root,'inventory-core.js'));
 for(const f of ['commerce-core.js','simple-core.js','corrections-core.js'])I=require(path.join(root,f))(I);
 const lots=[],issues=[];
 for(const l of data?.lots||[]){try{
  const b=I.reconciliation(data,l.id),active=r=>r.status!=='cancelled'&&r.status!=='deleted',sum=(rows,key)=>rows.reduce((n,r)=>n+(Number(r[key])||0),0),opening=I.opening(data,l.id),adjustments=(data.lotStockAdjustments||[]).filter(r=>r.lotId===l.id&&active(r)),sales=I.sales(data,l.id);lots.push({lot:l.id,produced:b.produced,sold:b.sold,samples:b.used,deliveredOrders:b.orderDelivered||0,stock:b.total,transit:b.transit,difference:b.unexplained,configured:b.configured,opening:opening?sum(opening.rows||[],'quantity'):null,adjustments:sum(adjustments.filter(r=>r.source!=='partner-order'),'delta'),historicalSales:sum(sales.filter(r=>r.mode==='historical'),'quantity'),directSales:sum(sales.filter(r=>r.mode!=='historical'),'quantity'),locations:b.rows.map(r=>({location:r.location,tag:r.tag,bottles:r.quantity,samples:r.sampleQuantity||0}))});
  if(b.unexplained)issues.push({lot:l.id,type:'reconciliation',bottles:b.unexplained});
  if(!b.configured)issues.push({lot:l.id,type:'missing-count'});
  for(const r of b.stockWarnings||[])issues.push({lot:l.id,type:'negative-stock',location:r.location,bottles:r.quantity});
  for(const s of I.sales(data,l.id)){if(s.priceKnown!==false&&s.priceCents!=null){const expected=Math.round(s.quantity*s.priceCents/(s.priceBasis==='box'?6:1));if(expected!==s.totalCents)issues.push({lot:l.id,type:'sale-amount-mismatch',record:s.id,expectedCents:expected,actualCents:s.totalCents});}}
 }catch(e){issues.push({lot:l.id,type:'calculation-error',message:e.message});}}
 return{lots,issues,readOnly:true};
}
module.exports={inspect};
