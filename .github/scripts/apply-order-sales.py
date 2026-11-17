import hashlib,json
from pathlib import Path
changes=json.loads(Path('.maintenance/order-sales-delta.json').read_text())
for c in changes:
 p=Path(c['path']);assert not p.is_absolute() and '..' not in p.parts
 old=p.read_text();h=hashlib.sha256(old.encode()).hexdigest()
 if h==c['after']:continue
 assert h==c['before'],str(p)+' differs from reviewed baseline'
 new=old
 for start,end,value in reversed(c['ops']):new=new[:start]+value+new[end:]
 assert hashlib.sha256(new.encode()).hexdigest()==c['after'],str(p)+' patch integrity failed'
 p.write_text(new)
print('Applied',len(changes),'hash-verified source changes; no production records accessed')
