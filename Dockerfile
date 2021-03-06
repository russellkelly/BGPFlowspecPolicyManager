FROM ubuntu:16.04

MAINTAINER Russell Kelly (russell@arrcus.com)

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install -y apt-utils && apt-get install -y curl
RUN apt-get update
RUN apt-get install -qy --no-install-recommends wget python git
RUN apt-get install -qy openssh-server
RUN apt-get install -qy openssh-client
RUN apt-get install -qy python3-pip
RUN apt-get install -qy python3-dev
RUN apt-get install -qy python3-flask
RUN apt-get install -qy libxml2-dev
RUN apt-get install -qy libxslt-dev
RUN apt-get install -qy libssl-dev
RUN apt-get install -qy libffi-dev
RUN apt-get install -qy sudo
RUN apt-get install -qy vim
RUN apt-get install -qy telnet
RUN apt-get install -qy curl
RUN apt-get install -qy shellinabox
RUN apt-get install -qy screen
RUN apt-get install -qy sshpass
RUN pip3 install --upgrade pip
RUN pip3 install --upgrade cryptography
RUN python3 -m easy_install --upgrade pyOpenSSL
RUN apt-get install -qy python-setuptools
RUN apt-get install -qy python3-setuptools
RUN pip3 install pyyaml --upgrade
RUN apt-get update -y
RUN apt-get install software-properties-common -y
RUN apt-get update
RUN apt-get install -qy default-jre
RUN echo debconf shared/accepted-oracle-license-v1-1 select true | debconf-set-selections
RUN apt-get clean
RUN pip3 install pyeapi
RUN pip3 install jsonrpc
RUN pip3 install jsonrpclib
RUN pip3 install requests


RUN export uid=1000 gid=1000 && \
    mkdir -p /home/flowspec && \
    echo "flowspec:x:${uid}:${gid}:flowspec,,,:/home/flowspec:/bin/bash" >> /etc/passwd && \
	echo 'flowspec:flowspec' | chpasswd \
    echo "flowspec:x:${uid}:" >> /etc/group && \
    echo "flowspec ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/flowspec && \
    chmod 0440 /etc/sudoers.d/flowspec && \
    chown ${uid}:${gid} -R /home/flowspec

USER flowspec

ENV HOME /home/flowspec
RUN sudo mkdir -p /var/run/sshd


WORKDIR /home/flowspec
RUN git clone https://github.com/Exa-Networks/exabgp.git
WORKDIR /home/flowspec/exabgp
RUN git checkout 4.0.10
RUN chmod +x setup.py
RUN sudo ./setup.py install
WORKDIR /home/flowspec

RUN cd /home/flowspec ; wget https://inmon.com/products/sFlow-RT/sflow-rt.tar.gz ; tar -xvzf sflow-rt.tar.gz


EXPOSE 179
EXPOSE 2022
EXPOSE 4200
EXPOSE 4201
EXPOSE 5000
EXPOSE 5001
EXPOSE 5002
EXPOSE 5003
EXPOSE 6343
EXPOSE 8008


COPY ConfigFiles/exabgp.env /usr/local/etc/exabgp/exabgp.env
COPY Scripts/KillPython.py /home/flowspec/Scripts/KillPython.py
COPY Scripts/RestartManager.py /home/flowspec/Scripts/RestartManager.py
COPY Scripts/RestartSflowRTCollector.py /home/flowspec/Scripts/RestartSflowRTCollector.py
COPY RestartContainerServices.sh /home/flowspec/RestartContainerServices.sh

ENTRYPOINT sudo service ssh restart && bash


