#!/bin/bash

# Usage:
#
# gen_certs 
#
# This script is used to generate key and certificate for HTTPS with Apache.
#

openssl req -new -newkey rsa:4096 -days 365 -nodes -x509 \
    -subj "/C=US/ST=Denial/L=Local/O=Undefined/CN=ddserver" \
    -keyout apache/server.key  -out apache/server.crt

echo "Created server.key and server.crt (self-signed)"
