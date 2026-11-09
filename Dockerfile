FROM node:22-alpine AS verify
WORKDIR /verify
COPY control.js ./control.js
COPY tests/costing.cjs ./tests/costing.cjs
COPY inventory-core.js lot-operations.js commerce-core.js commerce-ui.js ./
COPY tests/inventory.cjs tests/dispatch.cjs tests/commerce.cjs ./tests/
RUN node --check control.js && node --check inventory-core.js && node --check lot-operations.js && node tests/costing.cjs && node tests/inventory.cjs && node tests/dispatch.cjs && node --check commerce-core.js && node --check commerce-ui.js && node tests/commerce.cjs

COPY simple-core.js simple-lot.js ./
COPY tests/simple-lot.cjs ./tests/
RUN node --check simple-core.js && node --check simple-lot.js && node tests/simple-lot.cjs

COPY corrections-core.js corrections-ui.js ./
COPY tests/corrections.cjs tests/origin-stock.cjs tests/always-samples.cjs ./tests/
RUN node --check corrections-core.js && node --check corrections-ui.js && node tests/corrections.cjs && node tests/origin-stock.cjs && node tests/always-samples.cjs

COPY materials-core.js materials-ui.js ./
COPY tests/materials.cjs ./tests/
RUN node --check materials-core.js && node --check materials-ui.js && node tests/materials.cjs

COPY pdf-deps/ ./pdf-deps/
COPY .github/scripts/build-pdf.sh ./build-pdf.sh
RUN sh ./build-pdf.sh
COPY reports-data.js reports-pdf.js ./
RUN node --check reports-data.js && node --check reports-pdf.js

COPY packaging.js device-backup.js pwa.js ./
COPY tests/device-packaging.cjs ./tests/
RUN node --check packaging.js && node --check pwa.js && node --check device-backup.js && node tests/device-packaging.cjs

COPY server.cjs shared.js documents-store.cjs partner-report.cjs state-audit.cjs ./
COPY tests/shared-server.cjs ./tests/
RUN node --check server.cjs && node --check shared.js && node --experimental-sqlite tests/shared-server.cjs

COPY contacts-core.js executive-core.js office-ui.js office-nav.js ./
COPY tests/office.cjs ./tests/
RUN node --check office-ui.js && node --check office-nav.js && node tests/office.cjs

COPY contacts-import.js ./
COPY tests/contact-import.cjs ./tests/
RUN node --check contacts-import.js && node tests/contact-import.cjs

COPY tests/documents.cjs ./tests/
RUN node --check documents-store.cjs && node --experimental-sqlite tests/documents.cjs

COPY orders-core.js orders-ui.js ./
COPY tests/orders.cjs ./tests/
RUN node --check orders-core.js && node --check orders-ui.js && node tests/orders.cjs

COPY suppliers-core.js suppliers-ui.js ./
COPY tests/suppliers.cjs ./tests/
RUN node --check suppliers-core.js && node --check suppliers-ui.js && node tests/suppliers.cjs

FROM nginx:alpine AS static
# Preserve previous modules and data keys. Publish the tested lot workspace.
COPY index.html /usr/share/nginx/html/legacy.html
COPY control.html /usr/share/nginx/html/index.html
COPY control.css /usr/share/nginx/html/control.css
COPY production.css lot-operations.css commerce.css /usr/share/nginx/html/
COPY --from=verify /verify/inventory-core.js /verify/lot-operations.js /verify/commerce-core.js /verify/commerce-ui.js /usr/share/nginx/html/
COPY --from=verify /verify/control.js /usr/share/nginx/html/control.js
COPY ["EB logo.jpg", "EB espadin.jpg", "EB Cup.jpg", "EB DB.jpg", "/usr/share/nginx/html/"]
COPY simple-core.js simple-lot.js simple-lot.css /usr/share/nginx/html/
COPY corrections-core.js corrections-ui.js corrections.css /usr/share/nginx/html/
COPY materials.html materials-core.js materials-ui.js materials.css /usr/share/nginx/html/
COPY reports-data.js reports-pdf.js /usr/share/nginx/html/
COPY --from=verify /verify/vendor /usr/share/nginx/html/vendor
COPY app.webmanifest instalar.html packaging.js device-backup.js pwa.js pwa.css /usr/share/nginx/html/
COPY icons/ /usr/share/nginx/html/icons/
COPY office.html office.css office-ui.js office-nav.js contacts-core.js executive-core.js /usr/share/nginx/html/
COPY contacts-import.js /usr/share/nginx/html/
COPY documents.html documents-ui.js documents.css /usr/share/nginx/html/
COPY orders.html orders-core.js orders-ui.js orders.css /usr/share/nginx/html/
COPY edit-return.js /usr/share/nginx/html/
COPY suppliers.html suppliers-core.js suppliers-ui.js suppliers.css /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN set -eu; nginx; \
    for asset in suppliers.html suppliers-core.js suppliers-ui.js suppliers.css edit-return.js orders.html orders-core.js orders-ui.js orders.css documents.html documents-ui.js documents.css contacts-import.js vendor/fflate.js office.html office.css office-ui.js office-nav.js contacts-core.js executive-core.js app.webmanifest instalar.html packaging.js device-backup.js pwa.js pwa.css icons/eb-180.png icons/eb-192.png icons/eb-512.png icons/eb-maskable-512.png reports-data.js reports-pdf.js vendor/jspdf.umd.min.js vendor/jspdf.plugin.autotable.min.js materials.html materials-core.js materials-ui.js materials.css corrections-core.js corrections-ui.js corrections.css simple-core.js simple-lot.js index.html control.js control.css production.css lot-operations.css inventory-core.js lot-operations.js commerce-core.js commerce-ui.js commerce.css legacy.html 'EB%20logo.jpg' 'EB%20espadin.jpg' 'EB%20Cup.jpg' 'EB%20DB.jpg'; do \
      wget -q -O /tmp/eb-resource "http://127.0.0.1/$asset"; \
      test -s /tmp/eb-resource; \
      echo "HTTP 200 VERIFIED: $asset"; \
    done; \
    nginx -s stop; rm -f /tmp/eb-resource
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

FROM node:22-alpine AS shared
WORKDIR /app
COPY --from=static /usr/share/nginx/html/ ./public/
COPY server.cjs documents-store.cjs partner-report.cjs state-audit.cjs ./
COPY shared.js shared.css ./public/
ENV PORT=80
EXPOSE 80
CMD ["node", "--experimental-sqlite", "server.cjs"]
