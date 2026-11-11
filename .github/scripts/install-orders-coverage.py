from pathlib import Path
p=Path('orders.html');s=p.read_text()
if '/orders-coverage.js' not in s:
 marker='<script type="application/x-eb-shared" src="/orders-ui.js'
 assert s.count(marker)==1
 s=s.replace(marker,'<script type="application/x-eb-shared" src="/orders-coverage.js?v=coverage1"></script>'+marker,1)
 s=s.replace('</head>','<link rel="stylesheet" href="/orders-coverage.css?v=coverage1"></head>',1)
 s=s.replace('/orders-ui.js?v=quota-journal1','/orders-ui.js?v=coverage1')
 p.write_text(s)
p=Path('orders-ui.js');s=p.read_text()
if 'EBOrderCoverage?.render' not in s:
 marker=" document.querySelectorAll('[data-partner]').forEach"
 assert s.count(marker)==1
 s=s.replace(marker," window.EBOrderCoverage?.render(read().data);\n"+marker,1)
 p.write_text(s)
p=Path('Dockerfile');s=p.read_text()
if 'COPY orders-coverage.js ./' not in s:
 marker='FROM nginx:alpine AS static'
 s=s.replace(marker,'COPY orders-coverage.js ./\nCOPY tests/orders-coverage.cjs ./tests/\nRUN node --check orders-coverage.js && node tests/orders-coverage.cjs\n\n'+marker,1)
 marker='COPY nginx.conf'
 s=s.replace(marker,'COPY orders-coverage.js orders-coverage.css /usr/share/nginx/html/\n'+marker,1)
 s=s.replace('for asset in ','for asset in orders-coverage.js orders-coverage.css ',1)
 p.write_text(s)
print('Read-only order coverage installed. Save, synchronization and inventory rules unchanged.')
