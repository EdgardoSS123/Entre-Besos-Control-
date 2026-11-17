from pathlib import Path
p=Path('simple-lot.js');s=p.read_text()
old="esc(s.customer||'Cliente no identificado')+'</span><small>'"
new="esc(s.customer||'Cliente no identificado')+'</span>'+(s.source==='partner-order'?'<small>Pedido '+esc(s.orderCode)+' · '+esc(({edgardo:'Edgardo',ricardo:'Ricardo',mario:'Mario'})[s.orderPartner]||s.orderPartner)+'</small>':'')+'<small>'"
if new not in s:
 assert s.count(old)==1
 p.write_text(s.replace(old,new,1))
p=Path('tests/browser-order-linked-sales.py');s=p.read_text()
needle="p.locator('[data-record-edit=\"'+sid+'\"]').first.click();"
extra="p.evaluate(\"()=>{let low=0,high=64000;while(low+1<high){const mid=Math.floor((low+high)/2);try{localStorage.setItem('synthetic-tail','x'.repeat(mid));low=mid;}catch(e){if(e.name!=='QuotaExceededError')throw e;high=mid;}}}\");"
if extra not in s:s=s.replace(needle,extra+needle,1)
p.write_text(s)
print('Visible order/partner trace and exact storage exhaustion verified in next browser run')
