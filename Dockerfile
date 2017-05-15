FROM python:3-alpine
RUN apk add --update tar
RUN apk add --update curl
RUN apk add --update alpine-sdk
RUN apk add --update python-dev

ENV GEOS_VERSION 3.6.1

RUN mkdir -p /usr/src/app \
    && cd /usr/src \
    && curl -f -L -O http://download.osgeo.org/geos/geos-$GEOS_VERSION.tar.bz2 \
    && tar jxf geos-$GEOS_VERSION.tar.bz2 \
    && cd /usr/src/geos-$GEOS_VERSION \
    && ./configure \
    && make \
    && make install \
    && rm -rf /src

WORKDIR /io
CMD ["/io/build-linux-wheels.sh"]

RUN apk add --update postgresql-dev

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
COPY requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /usr/src/app
CMD python3 tornado_app.py