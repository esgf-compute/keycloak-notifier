ARG BASE_IMAGE
FROM $BASE_IMAGE

RUN conda update -n base -c defaults conda && \
      conda install -c conda-forge \
      requests-oauthlib slackclient python=3.7 && \
      conda clean -y -a

COPY notifier.py .

ENTRYPOINT ["python", "notifier.py"]
