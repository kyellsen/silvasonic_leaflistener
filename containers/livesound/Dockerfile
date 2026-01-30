FROM alpine:latest

# Install Icecast and mailcap (for mime definitions)
RUN apk add --no-cache icecast mailcap

# Create directory for logs if it doesn't exist (default in some configs)
RUN mkdir -p /var/log/icecast && \
    chown -R icecast:icecast /var/log/icecast

# Icecast runs as 'icecast' user by default in Alpine package
USER icecast

ENTRYPOINT ["icecast", "-c", "/etc/icecast.xml"]
