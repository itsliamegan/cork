FROM ubuntu:24.04

ENV container=podman
RUN echo '#!/bin/sh\nexit 0' > /usr/sbin/policy-rc.d

RUN apt-get update && apt-get install -y \
	systemd \
	systemd-sysv \
	curl \
	git \
	nginx \
	&& apt-get clean \
	&& rm -rf /var/lib/apt/lists/*

ENV UV_INSTALL_DIR=/opt/uv/bin
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/opt/uv/bin:${PATH}"
ENV UV_PYTHON_INSTALL_DIR=/opt/uv/python

RUN useradd --system --user-group cork

RUN mkdir -p /var/lib/cork
RUN chown -R cork:cork /var/lib/cork

ENV UV_PROJECT_ENVIRONMENT=/opt/cork/venv
WORKDIR /opt/cork/

COPY .python-version pyproject.toml uv.lock ./

RUN uv python install
RUN uv sync --locked --no-install-project --no-default-groups --group backup
RUN echo /srv/cork > "$(venv/bin/python -c 'import sysconfig; print(sysconfig.get_path("purelib"))')/cork.pth"

COPY etc/cork.service /etc/systemd/system/cork.service
COPY etc/cork.socket /etc/systemd/system/cork.socket
COPY etc/cork.dev.conf /etc/systemd/system/cork.service.d/dev.conf

COPY etc/nginx.dev.conf /etc/nginx/sites-available/cork

RUN ln -s /etc/nginx/sites-available/cork /etc/nginx/sites-enabled/ \
	&& rm -f /etc/nginx/sites-enabled/default

RUN mkdir -p /etc/systemd/system/multi-user.target.wants
RUN mkdir -p /etc/systemd/system/sockets.target.wants

RUN ln -fs /etc/systemd/system/cork.service /etc/systemd/system/multi-user.target.wants/cork.service
RUN ln -fs /etc/systemd/system/cork.socket /etc/systemd/system/sockets.target.wants/cork.socket

EXPOSE 80
STOPSIGNAL SIGRTMIN+3

COPY etc/entry.sh /usr/local/bin/entry.sh
RUN chmod +x /usr/local/bin/entry.sh
CMD ["/usr/local/bin/entry.sh"]
