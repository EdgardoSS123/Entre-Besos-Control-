from pathlib import Path
p=Path('tests/browser-documents.py');s=p.read_text()
old="expect(a.locator('#docs-dialog')).to_have_count(0);expect(a.locator('.docs-file')).to_contain_text('Vigente');expect(a.locator('#docs-title')).to_have_text('IMPI')"
new="expect(a.locator('#docs-dialog')).to_have_count(0);expect(a.locator('#docs-title')).to_have_text('Certificados');expect(a.locator('.docs-file')).to_have_count(0);a.locator('[data-category=\"IMPI\"]').click();expect(a.locator('.docs-file')).to_contain_text('Vigente');expect(a.locator('#docs-title')).to_have_text('IMPI')"
if new not in s:
    assert s.count(old)==1
    p.write_text(s.replace(old,new,1))
print('Document regression retains previous category after saving; verifies moved file under IMPI and exact byte download. No application behavior relaxed.')
