import base64,gzip,hashlib,json
from pathlib import Path
raw=gzip.decompress(base64.b64decode(Path('.maintenance/final-audit.b64').read_text(),validate=True))
sha='f71d7bf014ad5c957a5b00af25f1d6bddbe5a3e913e99b7e607a9b710a90bc89'
assert hashlib.sha256(raw).hexdigest()==sha
marker=Path('.maintenance/final-applied.sha');changes=json.loads(raw)
if not marker.exists():
    for c in changes:
        p=Path(c['path']);assert not p.is_absolute() and '..' not in p.parts
        old=p.read_text() if p.exists() else ''
        current=hashlib.sha256(old.encode()).hexdigest() if p.exists() else None
        if current!=c['after']:
            assert current==c['before'],str(p)+' changed since reviewed baseline'
            new=old
            for start,end,replacement in reversed(c['ops']):new=new[:start]+replacement+new[end:]
            assert hashlib.sha256(new.encode()).hexdigest()==c['after'],str(p)
            p.parent.mkdir(parents=True,exist_ok=True);p.write_text(new)
    marker.write_text(sha)
else:assert marker.read_text()==sha
Path('/tmp/eb-final-paths.json').write_text(json.dumps([c['path'] for c in changes]))
print('PASS reviewed integration:',len(changes),'files; no production data accessed')
