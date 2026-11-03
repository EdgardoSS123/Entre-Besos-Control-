FROM node:22-alpine AS verify
WORKDIR /verify
COPY control.js ./control.js
COPY tests/costing.cjs ./tests/costing.cjs
RUN node --check control.js && node tests/costing.cjs

FROM nginx:alpine
# Preserve previous modules and data keys. Publish the tested lot workspace.
COPY index.html /usr/share/nginx/html/legacy.html
COPY control.html /usr/share/nginx/html/index.html
COPY control.css /usr/share/nginx/html/control.css
COPY production.css /usr/share/nginx/html/production.css
COPY --from=verify /verify/control.js /usr/share/nginx/html/control.js
COPY ["EB logo.jpg", "EB espadin.jpg", "EB Cup.jpg", "EB DB.jpg", "/usr/share/nginx/html/"]
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN set -eu; nginx; \
    for asset in index.html control.js control.css production.css legacy.html 'EB%20logo.jpg' 'EB%20espadin.jpg' 'EB%20Cup.jpg' 'EB%20DB.jpg'; do \
      wget -q -O /tmp/eb-resource "http://127.0.0.1/$asset"; \
      test -s /tmp/eb-resource; \
      echo "HTTP 200 VERIFIED: $asset"; \
    done; \
    nginx -s stop; rm -f /tmp/eb-resource
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
