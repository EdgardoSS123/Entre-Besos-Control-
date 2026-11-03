FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
# Publish the original brand files as well as the HTML.
COPY ["EB logo.jpg", "EB espadin.jpg", "EB Cup.jpg", "EB DB.jpg", "/usr/share/nginx/html/"]
RUN test -s '/usr/share/nginx/html/EB logo.jpg' && test -s '/usr/share/nginx/html/EB espadin.jpg' && test -s '/usr/share/nginx/html/EB Cup.jpg' && test -s '/usr/share/nginx/html/EB DB.jpg'
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
