FROM centos

RUN yum update -y \
 && yum install python3 -y \
 && yum install epel-release -y

RUN yum install -y clamav clamav-update

RUN sed -i -e "s/^Example/#Example/" /etc/freshclam.conf \
 && sed -i -e "s/^Example/#Example/" /etc/clamd.d/scan.conf

RUN freshclam

RUN yum install -y wget \
 && wget -P /tmp https://www.eicar.org/download/eicar.com

ENTRYPOINT ["/bin/bash", "-l", "-c"]
