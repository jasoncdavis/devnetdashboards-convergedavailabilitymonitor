FROM python:3.9-slim-buster

COPY ./docker/python/install-packages.sh /project/
RUN chmod +x /project/install-packages.sh

RUN /project/install-packages.sh

ADD ./requirements.txt /project/requirements.txt
RUN pip install -r /project/requirements.txt #only re-executed if the file changes

ADD ./src /project/code

RUN git clone --branch json-output https://github.com/bonkf/fping.git /project/code/fping
RUN cd /project/code/fping && ./autogen.sh && ./configure && make && make install
# Overwrite optionsconfig.py with Docker-specific version
ADD ./src/optionsconfig-docker.yaml /project/code/optionsconfig.yaml
# ADD ./html /project/code/html
ADD ./images /project/code/images

CMD tail -f /dev/null