FROM python:3.11-slim-bookworm

# Install Chromium for the undetected driver.  A Debian base is used because
# undetected-chromedriver relies on glibc and is unreliable on Alpine/musl.
RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*

ENV LEETCODE_HEADLESS=1
ENV LEETCODE_DRIVER=undetected
ENV CHROME_BIN=/usr/bin/chromium

WORKDIR /app

# install python dependencies
RUN pip3 install --upgrade pip
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# copy over files last
COPY /data ./data
COPY /main ./main
COPY /problem_data ./problem_data
COPY screenshots ./screenshots

# run the application
ENTRYPOINT ["python3", "main/runner.py"]
