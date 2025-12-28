FROM apache/hadoop:3.4.1
USER root

# Install dependencies for downloading and installing Conda
# Note: We still fix the basic repos just in case Hadoop image needs them for basic ops,
# but we no longer rely on 'yum' for the Python 3.8 installation itself.
RUN sed -i 's/mirrorlist/#mirrorlist/g' /etc/yum.repos.d/*.repo && \
    sed -i 's|#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|g' /etc/yum.repos.d/*.repo && \
    sed -i 's|baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|g' /etc/yum.repos.d/*.repo

# Install Miniconda (Python 3.8 version)
# We use a specific older version of Miniconda that defaults to Python 3.8
RUN curl -L https://repo.anaconda.com/miniconda/Miniconda3-py38_4.12.0-Linux-x86_64.sh -o miniconda.sh && \
    bash miniconda.sh -b -p /opt/conda && \
    rm miniconda.sh

# Update PATH and create global symlinks
ENV PATH="/opt/conda/bin:${PATH}"
RUN ln -sf /opt/conda/bin/python3 /usr/bin/python3 && \
    ln -sf /opt/conda/bin/pip3 /usr/bin/pip3 && \
    ln -sf /opt/conda/bin/python3 /usr/bin/python

# Pre-install numpy for Spark executors
RUN /opt/conda/bin/pip install --no-cache-dir numpy

USER hadoop
