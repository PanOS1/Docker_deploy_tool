FROM python:2.7
EXPOSE 5000
COPY simple_web_app.py /
RUN pip install flask
RUN pip install redis
CMD ["python", "/simple_web_app.py"]
