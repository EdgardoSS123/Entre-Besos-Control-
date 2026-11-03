FROM node:22-alpine AS verify
WORKDIR /verify
COPY control.js ./control.js
COPY tests/costing.cjs ./tests/costing.cjs
COPY inventory-core.js lot-operations.js ./
COPY tests/inventory.cjs ./tests/inventory.cjs
RUN node --check control.js && node --check inventory-core.js && node --check lot-operations.js && node tests/costing.cjs && node tests/inventory.cjs

FROM nginx:alpine
# Preserve previous modules and data keys. Publish the tested lot workspace.
COPY index.html /usr/share/nginx/html/legacy.html
COPY control.html /usr/share/nginx/html/index.html
COPY control.css /usr/share/nginx/html/control.css
COPY production.css lot-operations.css /usr/share/nginx/html/
COPY --from=verify /verify/inventory-core.js /verify/lot-operations.js /usr/share/nginx/html/
COPY --from=verify /verify/control.js /usr/share/nginx/html/control.js
COPY ["EB logo.jpg", "EB espadin.jpg", "EB Cup.jpg", "EB DB.jpg", "/usr/share/nginx/html/"]
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN set -eu; nginx; \
    for asset in index.html control.js control.css production.css lot-operations.css inventory-core.js lot-operations.js legacy.html 'EB%20logo.jpg' 'EB%20espadin.jpg' 'EB%20Cup.jpg' 'EB%20DB.jpg'; do \
      wget -q -O /tmp/eb-resource "http://127.0.0.1/$asset"; \
      test -s /tmp/eb-resource; \
      echo "HTTP 200 VERIFIED: $asset"; \
    done; \
    nginx -s stop; rm -f /tmp/eb-resource
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
