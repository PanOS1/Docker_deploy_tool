# Docker_deploy_tool
A simple tool for building a docker image from a Dockerfile and staring multimple containers from it.
The tool reads a configuration file *web_conf.yml* and creates/runs the specified number of containers
and performs a basic health check by calling a **check status** url. Appart from creating docker images 
containers and running them it also keeps the specified number of containers specified in *web_conf.yml*. 

## Parameters

* -b : Read the *web_conf.yml* and build/run containers accordingly
* --logs : Show the logs from all containers
* --stats ; Show stats from all containers

## Example Configuration
The following configuraion will deploy 2 instances of redis and 4 instaces of a simple web application which
will be connected to the redis_1 container. Each deployed web application (container) uses the redis in order 
to increase and get a **hits** counter.

e.g Hello Container World! I have been seen **3** times.  

``` yaml
---
0_redis:
  build: false
  instances: 2
  image: redis
  tag: latest
  internal_port: 6379
  external_port: 6379
  check: False

1_web_app:
  build: true
  instances: 4
  image: simple_web_app
  tag: 0.0.1
  internal_port: 5000
  external_port: 8000
  links:
    - redis_1
  check_url: "http://127.0.0.1:{port}/status"
```

### Variables
* build : if **true** builds a docker image from the Dockerfile in files folder else pulls image from docker registry
* instances : the required number of docker containers
* image : the name of the image to be build/pulled
* tag : tag of the image to be build/pulled
* internal_port : internal port of the service running in container(s)
* external_port : external port (exposed port) of the docker container. It is used as a staring point and every new container uses the (+1) port.
* links : a list of docker containers to be linked with this container
* check_url : if defined it will be used to check tha health of its running containers (web apps)
