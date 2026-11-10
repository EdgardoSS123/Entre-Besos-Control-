from pathlib import Path
p=Path('tests/browser-slow-supplier-save.py');s=p.read_text()
old="if(drop){reply.resume();reply.on('end',()=>res.destroy());return;}"
new="if(drop){reply.resume();reply.on('end',()=>{res.writeHead(503,{'content-type':'application/json'});res.end(JSON.stringify({error:'Synthetic gateway lost the commit acknowledgement'}));});return;}"
if new not in s:
 assert s.count(old)==1
 s=s.replace(old,new,1)
s=s.replace("# Actual network reply lost AFTER a durable commit: recover by GET receipt.","# Commit succeeded but the gateway cannot deliver its acknowledgement: recover by GET receipt.")
p.write_text(s)
print('Lost acknowledgement now explicitly returns HTTP 503 after commit; tests still require exactly one write and a matching durable receipt.')
