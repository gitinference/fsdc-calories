FROM nginx

# COPY /etc/letsencrypt/live/ /etc/letsencrypt/live/

CMD ["nginx", "-g", "daemon off;"]