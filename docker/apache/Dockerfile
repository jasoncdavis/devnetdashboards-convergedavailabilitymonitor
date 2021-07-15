FROM httpd:alpine

RUN  apk update && apk upgrade && \
     rm -rf /var/cache/apk/*

RUN  sed -i \
        -e 's/^#\(Include .*httpd-ssl.conf\)/\1/' \
        -e 's/^#\(LoadModule .*mod_ssl.so\)/\1/' \
        -e 's/^#\(LoadModule .*mod_socache_shmcb.so\)/\1/' \
        -e 's/^#\(ServerName www.example.com:80\)/ServerName ddserver:443/' \
        -e 's/^\(Listen 80\)/#\1/' \
        conf/httpd.conf

RUN  sed -i \
        -e 's/^\(ServerName www.example.com:443\)/ServerName ddserver:443/' \
        conf/extra/httpd-ssl.conf

COPY  ./server.key /usr/local/apache2/conf/
COPY  ./server.crt /usr/local/apache2/conf/

#CMD  [ "/usr/sbin/httpd", "-D", "FOREGROUND"]