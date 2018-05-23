.. centos install guide

==========================
Installing Red on CentOS 7
==========================

.. warning:: For safety reasons, DO NOT install Red with a root user. Instead, `make a new one <https://access.redhat.com/documentation/en-US/Red_Hat_Enterprise_Linux/4/html/Step_by_Step_Guide/s1-starting-create-account.html>`_.

---------------------------
Installing pre-requirements
---------------------------

.. code-block:: none

    yum -y groupinstall development
    yum -y install https://centos7.iuscommunity.org/ius-release.rpm
    yum -y install yum-utils wget which python35u python35u-pip python35u-devel openssl-devel libffi-devel git java-1.8.0-openjdk
    sh -c "$(wget https://gist.githubusercontent.com/mustafaturan/7053900/raw/27f4c8bad3ee2bb0027a1a52dc8501bf1e53b270/latest-ffmpeg-centos6.sh -O -)"

.. include:: red_install.rst