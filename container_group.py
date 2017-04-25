import docker
import requests
from requests.exceptions import *
import logging 

class ContainerGroup(object):

    """ Class for maanging a group of containers """
    
    def __init__(self,configuration):
        """ Read configuration dict and initiate class variables """
        self.dockerfile_path = "./files/."
        self.client = docker.from_env()
        self.conf_dict = configuration
        self.image = configuration['image']
        self.build = configuration['build']
        self.check_url = configuration.get('check_url', '')
        self.tag = configuration['tag']
        self.instances = int(configuration['instances'])
        self.internal_port = str(configuration['internal_port'])
        self.external_port = int(configuration['external_port'])
        self.links_list = configuration.get('links',[])
        self.container_names = []
        self.links_dict = {x: x.split('_')[0] for x in self.links_list}
        self.tag_name = self.image+':'+self.tag
        self.image_short_id = None
        self.image_name = None
        self.recreate_containers = False
        self.logger = logging.getLogger("deploy_web_app."+__name__)
        for i in range(self.instances):
            self.container_names.append(self.image+'_'+str(i))
        assert isinstance(self.build, bool)
        assert isinstance(self.image, str)
        assert isinstance(self.tag, str)
            

    def get_configuration(self):
        return self.conf_dict

    def build_image(self):
        """ method for either building an image from a Dockerfile
        or pulling the image from the public registry """
         
        target_image = None 
        if self.build:
            target_image = self.client.images.build(path=self.dockerfile_path,tag=self.tag_name,pull=True)
        else:
            target_image = self.client.images.pull(self.image, tag=self.tag)
        self.iamge_short_id = target_image.short_id
        self.image_name = target_image.tags[0] 
        if self.image_name != self.tag_name:
            self.recreate_containers = True
            self.tag_name = self.image_name
        return self.iamge_short_id, self.image_name

    def stop_remove_by_name(self,container_name):
        container = self.client.containers.get(container_name)
        container.stop()
        container.remove()

    def stop_and_remove(self,containers):
        """ method that gets as input a dictionary of caontainers
            and stops and removes them """
        for container in containers.values():
            con_name = container.name
            if container.status == 'running':
                container.stop()
            container.remove()

    def is_new_link(self,container):
        """ Checks if container is already 
            linked to the provided link """
        container_links = container.attrs['HostConfig']['Links']
        if container_links:
            for link in self.links_list:
                for container_link in container_links:
                    link = link.split(':')[0]
                    container_link = container_link.split(':')[0]
                    if link not in container_link: 
                        return True
        return True
         
    def run_containers(self):
        """ Method for starting the required number of containers """
        containers = self.get_containers()
        active_containers = []
        base_port = self.external_port
        for container_name in self.container_names:
            create_container = False
            container = containers.get(container_name, None)
            # Create and run container
            if not container:
                if self.recreate_containers:
                    self.stop_remove_by_name(container_name)
                create_container = True
            elif container.status == 'exited' or container.status == 'created' or container.status == 'running':
                if not self.is_new_link(container):
                    active_containers.append(container)
                    del containers[container_name]
                    if container.status == 'exited':
                        try:
                            container.start()
                        except docker.errors.NotFound:
                            self.logger.error("Container not found")
                            exit(-1)    
                else:
                    self.stop_remove_by_name(container_name)
                    del containers[container_name]
                    create_container = True
            if create_container: 
                self.logger.info("Creating and starting containeri {}".format(container_name))
                container_hostname = container_name.replace('_','-')
                while True:
                    try:
                        container = self.client.containers.run(self.tag_name,detach=True,hostname=container_hostname, \
                                                               name=container_name,ports={self.internal_port+'/tcp': base_port}, \
                                                               links=self.links_dict)
                    except docker.errors.ImageNotFound:
                        self.logger.error("Image not found. Exiting...")
                        exit(-1)
                    except docker.errors.APIError:
                        self.stop_remove_by_name(container_name) 
                        continue
                    break
                active_containers.append(container)    
            base_port = base_port + 1
        # Stop remaining containers
        self.stop_and_remove(containers)
        return active_containers

    def get_containers(self):
        """ Returns a dictionary of containers with key 
            the name of the container and value the container object """
        all_containers_list = self.client.containers.list(all=True,filters={'ancestor':self.tag_name})
        named_containers = {_c.name:_c for _c in all_containers_list}
        return named_containers

    def is_app_healthy(self,url):
        try:
            r = requests.get(url)
            if r.text != 'OK':
                return False
        except ConnectionError:
            return False
        return True    
    
    def check_health(self):
         """ method in order to check the health of containers """
         status = None
         health = []
         if self.check_url:
             for i in range(self.instances):
                url = self.check_url.format(port=self.external_port+i)
                if self.is_app_healthy(url):
                    health.append(self.image+'_'+str(i)+' OK')
                    status = True
                else:
                    health.append(self.image+'_'+str(i)+' NOT OK')
                    status = False
         health = '\n'.join(health)
         return status, health

    

    def check_communication(self):
        """ method for checking if communication 
            with docker deamon is ok. 
            Return True -> OK, False -> NOT OK """
        try:
            result = self.client.ping()
            return result
        except docker.errors.APIError:
            self.logger.error("API Version")
            exit(1)
        except ConnectionError:
            self.logger.error("communicating to docker deamon. Check docker deamon is running")
            exit(1)

    def get_logs_stream(self):
        """ Returns an dictionary of blocking generators on which 
             you can iterate over to retrieve log output as 
             it happens from all containers."""
        log_generators = {}
        containers = self.get_containers()
        for name,container in containers.items():
            log_generators[name] = container.logs(stdout=True,stderr=True,\
                                                 stream=True,timestamps=True,\
                                                 follow=True)
        return log_generators
