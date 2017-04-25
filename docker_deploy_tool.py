#!/usr/bin/python

import os
import yaml
import signal
import time
import sys
from container_group import *
from requests.exceptions import *
import multiprocessing
import logging
import argparse


def print_log_stream(generator):
    for line in generator:
        print line

if __name__ == "__main__":
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("deploy_web_app")
    logger.info("Reading configuration")    
    
    parser = argparse.ArgumentParser(description="""A simple tool for deploying a set of containers as 
                                                    defined in web_conf.yml""",)
    parser.add_argument('--logs', dest='containers_logs', action="store_true", \
                        default=False, help="Show logs from all running containers")
    parser.add_argument('--stats', dest='containers_stats', action="store_true", \
                        default=False, help="Show stats from all running containers")
    parser.add_argument('-b', dest='build', action="store_true", \
                        default=False, help="Build and run containers as described in web_conf.yml")
    results = parser.parse_args()

    # Read yaml configuration file
    configuration = yaml.load(open('web_conf.yml','r'))
    logs_stream_generators = {}
    for target in configuration.keys():
        logger.info("Target: {0}".format(target))
        grp = ContainerGroup(configuration[target])
        if not grp.check_communication():
            logger.error("*** ERROR can't ping docker deamon")
            sys.exit(0)
        else:
            logger.info("* Communication with docker deamon OK")
        if results.build:
            short_id, created_tag = grp.build_image()
            logger.info("Image ready: {0} {1}".format(short_id,created_tag))
            active_containers = grp.run_containers()
            for container in active_containers:
                logger.info("Container {0} running".format(container.name))
    
        time.sleep(3)   
        status, description = grp.check_health()
        if description:
            print "\n**** WEB APP HEALTH STATUS ****"
            print description 
            print "*******************************\n"
        logs_stream_generators.update(grp.get_logs_stream())
   
    if results.containers_logs: 
        jobs = []
        for container_name, log_stream_generator in logs_stream_generators.items():
            multiprocessing.log_to_stderr(logging.ERROR)
            p = multiprocessing.Process(name=container_name, target=print_log_stream, args=(log_stream_generator,))
            p.daemon = True
            p.start()
        try:
            while(True):
                time.sleep(1)
        except KeyboardInterrupt:
            for p in jobs:
                p.terminate()
                p.join()
            logger.info("Bye Bye.. Have a nice day.")

    if results.containers_stats:
        # Monitoring Containers
        os.system('docker stats')
