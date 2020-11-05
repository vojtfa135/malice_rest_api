FROM centos

RUN yum update -y \
 && yum install python3 -y \
 && yum install epel-release -y

RUN yum install -y clamav clamav-update

RUN sed -i -e "s/^Example/#Example/" /etc/freshclam.conf \
 && sed -i -e "s/^Example/#Example/" /etc/clamd.d/scan.conf

RUN yum install -y wget \
 && wget -P /tmp https://www.eicar.org/download/eicar.com

RUN freshclam

RUN mkdir /scan

COPY scan.py /scan

RUN mkdir /malware

WORKDIR /malware

ENTRYPOINT ["/usr/bin/python3", "/scan/scan.py", "--path"]
