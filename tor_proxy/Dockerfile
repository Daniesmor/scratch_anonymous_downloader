# Usa una imagen base
FROM alpine:latest

LABEL maintainer="daniesmor"

# Install system dependencies
RUN apk update && \
    apk add --no-cache tor && \
    rm -rf /var/cache/apk/


# Setting up Tor
COPY torrc /etc/tor/torrc

# Expose Tor (listen) port
EXPOSE 9050

# Setting up HEALTHCHECK
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python3", "./healthcheck_tor.py"]