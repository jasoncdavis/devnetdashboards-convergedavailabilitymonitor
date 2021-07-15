FROM mysql:latest

RUN chown -R mysql:root /var/lib/mysql

ARG MYSQL_DATABASE
ARG MYSQL_USER
ARG MYSQL_PASSWORD
ENV DB_USER=$MYSQL_USER
ENV DB_NAME=$MYSQL_DATABASE
ENV DB_PASS=$MYSQL_PASSWORD

ADD ./build-database.sql /etc/mysql/data.sql
RUN sed -i 's/MYSQL_DATABASE/'$DB_NAME'/g' /etc/mysql/data.sql
RUN sed -i 's/MYSQL_USER/'$DB_USER'/g' /etc/mysql/data.sql
RUN sed -i 's/MYSQL_PASSWORD/'$DB_PASS'/g' /etc/mysql/data.sql
RUN cp /etc/mysql/data.sql /docker-entrypoint-initdb.d

EXPOSE 3306