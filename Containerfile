FROM ubuntu:24.04

ENV container=podman
RUN echo '#!/bin/sh\nexit 0' > /usr/sbin/policy-rc.d

RUN apt-get update && apt-get install -y \
	systemd \
	systemd-sysv \
	curl \
	nginx \
	&& apt-get clean \
	&& rm -rf /var/lib/apt/lists/*

ENV UV_INSTALL_DIR=/opt/uv/bin
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/opt/uv/bin:${PATH}"
ENV UV_PYTHON_INSTALL_DIR=/opt/uv/python

RUN useradd --system --user-group cork

COPY cork/etc/cork.service /etc/systemd/system/cork.service
COPY cork/etc/cork.socket /etc/systemd/system/cork.socket

RUN sed -i '/^ProtectSystem\|^ProtectHome\|^PrivateTmp\|^ReadWritePaths/d' \
    /etc/systemd/system/cork.service

RUN mkdir -p /var/lib/cork
RUN chown -R cork:cork /var/lib/cork

WORKDIR /srv/

COPY luna/ luna/
COPY helios/ helios/
COPY cork/ cork/

RUN	chown -R cork:cork luna/
RUN	chown -R cork:cork helios/
RUN	chown -R cork:cork cork/

WORKDIR /srv/cork/

RUN uv python install
RUN uv sync --locked --no-default-groups --group backup
RUN chown -R cork:cork .venv/

COPY cork/etc/nginx.dev.conf /etc/nginx/sites-available/cork

RUN ln -s /etc/nginx/sites-available/cork /etc/nginx/sites-enabled/ \
	&& rm -f /etc/nginx/sites-enabled/default

RUN mkdir -p /etc/systemd/system/multi-user.target.wants
RUN mkdir -p /etc/systemd/system/sockets.target.wants

RUN ln -fs /etc/systemd/system/cork.service /etc/systemd/system/multi-user.target.wants/cork.service
RUN ln -fs /etc/systemd/system/cork.socket /etc/systemd/system/sockets.target.wants/cork.socket

EXPOSE 80
STOPSIGNAL SIGRTMIN+3

COPY cork/etc/entry.sh /usr/local/bin/entry.sh
RUN chmod +x /usr/local/bin/entry.sh
CMD ["/usr/local/bin/entry.sh"]
