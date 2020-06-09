FROM python:3.7-slim-buster

# set work directory
WORKDIR /usr/src/dms_backend
# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt update && apt -y install openssh-client git libudunits2-dev netcat-openbsd > /dev/null

COPY . .
RUN echo "\ngunicorn" >> requirements.txt
# install dependencies
RUN pip install -q -r requirements.txt
ENTRYPOINT ["/usr/src/dms_backend/entrypoint.sh"]
