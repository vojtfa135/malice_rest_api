####################################################
# GOLANG BUILDER
####################################################
FROM golang:1.11 as go_builder

RUN git clone --depth=1 https://github.com/malice-plugins/fsecure /go/src/github.com/malice-plugins/fsecure
#COPY . /go/src/github.com/malice-plugins/fsecure

WORKDIR /go/src/github.com/malice-plugins/fsecure
RUN go get -u github.com/golang/dep/cmd/dep && dep ensure
RUN go build -ldflags "-s -w -X main.Version=v$(cat VERSION) -X main.BuildTime=$(date -u +%Y%m%d)" -o /bin/avscan

####################################################
# PLUGIN BUILDER
####################################################
FROM ubuntu:bionic

LABEL maintainer "https://github.com/blacktop"

LABEL malice.plugin.repository = "https://github.com/malice-plugins/fsecure.git"
LABEL malice.plugin.category="av"
LABEL malice.plugin.mime="*"
LABEL malice.plugin.docker.engine="*"

# Create a malice user and group first so the IDs get set the same way, even as
# the rest of this may change over time.
RUN groupadd -r malice \
  && useradd --no-log-init -r -g malice malice \
  && mkdir /malware \
  && chown -R malice:malice /malware

# This version is the newest one according to their website, so this is totally fine
ENV FSECURE_VERSION 11.10.68
ENV FSECURE_DBUPDATE http://download.f-secure.com/latest/fsdbupdate9.run
ENV FSECURE_TAR https://download.f-secure.com/corpro/ls/ls11.10/fsls-${FSECURE_VERSION}-rtm.tar.gz
ENV WHATAMI "fsecure"

# Install Requirements
RUN buildDeps='wget rpm ca-certificates' \
  && apt-get update -qq \
  && apt-get install -yq $buildDeps lib32stdc++6 psmisc \
  && echo "===> Install F-Secure..." \
  && cd /tmp \
  && wget -q ${FSECURE_TAR} \
  && tar zxvf fsls-${FSECURE_VERSION}-rtm.tar.gz \
  && cd fsls-${FSECURE_VERSION}-rtm \
  && chmod a+x fsls-${FSECURE_VERSION} \
  && ./fsls-${FSECURE_VERSION} --auto standalone lang=en --command-line-only \
  && fsav --version \
  && echo "===> Update F-Secure..." \
  && cd /tmp \
  && wget -q ${FSECURE_DBUPDATE} \
  && mv fsdbupdate9.run /opt/f-secure/ \
  && echo "===> Clean up unnecessary files..." \
  && apt-get purge -y --auto-remove $buildDeps && apt-get clean \
  && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.gnupg

# Ensure ca-certificates is installed for elasticsearch to use https
RUN apt-get update -qq && apt-get install -yq --no-install-recommends ca-certificates \
  && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Change privileges on fsdbupdate9.run
RUN chmod 755 /opt/f-secure/fsdbupdate9.run

# Update F-Secure
RUN echo "===> Update F-Secure Database..." \
  && mkdir -p /opt/malice \
  && /etc/init.d/fsaua start \
  && /etc/init.d/fsupdate start \
  && /opt/f-secure/fssp/bin/dbupdate_lite \
  && /opt/f-secure/fsdbupdate9.run

# Add EICAR Test Virus File to malware folder
ADD https://secure.eicar.org/eicar.com.txt /malware/EICAR

COPY update.sh /opt/malice/update
COPY --from=go_builder /bin/avscan /bin/avscan

WORKDIR /malware

ENTRYPOINT [ "/bin/avscan" ]

####################################################
# https://download.f-secure.com/corpro/ls/trial/fsls-11.10.68-rtm.tar.gz

