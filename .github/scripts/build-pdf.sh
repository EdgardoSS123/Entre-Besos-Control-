#!/bin/sh
set -eu
if [ -f pdf-deps/package-lock.json ]; then
  npm ci --prefix pdf-deps --ignore-scripts --omit=dev --no-audit --no-fund
else
  npm install --prefix pdf-deps --ignore-scripts --omit=dev --no-audit --no-fund
fi
mkdir -p vendor
cp pdf-deps/node_modules/jspdf/dist/jspdf.umd.min.js vendor/jspdf.umd.min.js
cp pdf-deps/node_modules/jspdf-autotable/dist/jspdf.plugin.autotable.min.js vendor/jspdf.plugin.autotable.min.js
for lib in jspdf jspdf-autotable; do
  for name in LICENSE LICENSE.txt license.txt; do
    if [ -f "pdf-deps/node_modules/$lib/$name" ]; then cp "pdf-deps/node_modules/$lib/$name" "vendor/$lib-LICENSE.txt"; break; fi
  done
done
node --check vendor/jspdf.umd.min.js
node --check vendor/jspdf.plugin.autotable.min.js
