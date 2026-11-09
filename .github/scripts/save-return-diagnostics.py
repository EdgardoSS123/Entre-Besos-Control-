from pathlib import Path
p=Path('tests/browser-save-return.py');s=p.read_text()
s=s.replace("page.on('pageerror',lambda e:errors.append(str(e)))", "page.on('pageerror',lambda e:(print('PAGE ERROR:',str(e),flush=True),errors.append(str(e))))")
old="b.click();page.locator('#edit-price').fill('850')"
new="b.click();page.screenshot(path=str(OUT/f'after-edit-click-{engine}-{width}.png'));print('EDIT OPEN:',page.evaluate(\"()=>({dialogs:document.querySelectorAll('dialog').length,errors:document.querySelector('#simple-error')?.textContent,helper:typeof window.EBEditReturn,onclick:typeof document.querySelector('[data-record-edit=\\\"sale-return\\\"][data-kind=\\\"sale\\\"]')?.onclick})\"),flush=True);assert not errors,errors;page.locator('#edit-price').fill('850')"
assert old in s
s=s.replace(old,new,1)
p.write_text(s)
