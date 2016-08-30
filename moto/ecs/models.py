from __future__ import unicode_literals
import uuid
from datetime import datetime
import pytz

from moto.core import BaseBackend
from moto.ec2 import ec2_backends


class BaseObject(object):
    def camelCase(self, key):
        words = []
        for i, word in enumerate(key.split('_')):
            if i > 0:
                words.append(word.title())
            else:
                words.append(word)
        return ''.join(words)

    def gen_response_object(self):
        response_object = self.__dict__.copy()
        for key, value in response_object.items():
            if '_' in key:
                response_object[self.camelCase(key)] = value
                del response_object[key]
        return response_object

    @property
    def response_object(self):
        return self.gen_response_object()


class Cluster(BaseObject):
    def __init__(self, cluster_name):
        self.active_services_count = 0
        self.arn = 'arn:aws:ecs:us-east-1:012345678910:cluster/{0}'.format(cluster_name)
        self.name = cluster_name
        self.pending_tasks_count = 0
        self.registered_container_instances_count = 0
        self.running_tasks_count = 0
        self.status = 'ACTIVE'

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        response_object['clusterArn'] = self.arn
        response_object['clusterName'] = self.name
        del response_object['arn'], response_object['name']
        return response_object


class TaskDefinition(BaseObject):
    def __init__(self, family, revision, container_definitions, volumes=None, task_role_arn=None):
        self.family = family
        self.revision = revision
        self.arn = 'arn:aws:ecs:us-east-1:012345678910:task-definition/{0}:{1}'.format(family, revision)
        self.container_definitions = container_definitions
        if volumes is not None:
            self.volumes = volumes
        if task_role_arn is not None:
            self.task_role_arn = task_role_arn

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        response_object['taskDefinitionArn'] = response_object['arn']
        del response_object['arn']
        return response_object


class Service(BaseObject):
    def __init__(self, cluster, service_name, task_definition, desired_count, role=None, loadBalancers=None):
        self.cluster_arn = cluster.arn
        self.arn = 'arn:aws:ecs:us-east-1:012345678910:service/{0}'.format(service_name)
        self.name = service_name
        self.status = 'ACTIVE'
        self.running_count = desired_count
        self.task_definition = task_definition.arn
        self.desired_count = desired_count
        createdAt = datetime.now().replace(tzinfo=pytz.UTC).isoformat()
        self.events = [{
            "id": str(uuid.uuid4()),
            "createdAt": createdAt,
            "message": "service {} has reached a steady state.".format(self.name)
        }]
        if role:
            if role.startswith("arn:aws"):
                self.role_arn = role
            else:
                self.role_arn = 'arn:aws:iam::012345678910:role/{0}'.format(role)
        else:
            self.role_arn = ""
        self.load_balancers = loadBalancers or []
        self.pending_count = 0
        self.deployments = [{
            'id': str(uuid.uuid4()),
            'status': 'PRIMARY',
            'taskDefinition': self.task_definition,
            'desiredCount': self.desired_count,
            'pendingCount': self.pending_count,
            'runningCount': self.running_count,
            'createdAt': createdAt,
            'updatedAt': createdAt
        }]

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        del response_object['name'], response_object['arn']
        response_object['serviceName'] = self.name
        response_object['serviceArn'] = self.arn
        return response_object


class ContainerInstance(BaseObject):
    def __init__(self, ec2_instance_id):
        self.ec2_instance_id = ec2_instance_id
        self.status = 'ACTIVE'
        self.registeredResources = []
        self.agentConnected = True
        self.containerInstanceArn = "arn:aws:ecs:us-east-1:012345678910:container-instance/{0}".format(str(uuid.uuid1()))
        self.pendingTaskCount = 0
        self.remainingResources = []
        self.runningTaskCount = 0
        self.versionInfo = {
                    'agentVersion': "1.0.0",
                    'agentHash': '4023248',
                    'dockerVersion': 'DockerVersion: 1.5.0'
                }

        @property
        def response_object(self):
            response_object = self.gen_response_object()
            del response_object['name'], response_object['arn']
            return response_object


class ContainerInstanceFailure(BaseObject):
    def __init__(self, reason, container_instance_id):
        self.reason = reason
        self.arn = "arn:aws:ecs:us-east-1:012345678910:container-instance/{0}".format(container_instance_id)

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        response_object['reason'] = self.reason
        response_object['arn'] = self.arn
        return response_object


class EC2ContainerServiceBackend(BaseBackend):
    def __init__(self):
        self.clusters = {}
        self.task_definitions = {}
        self.services = {}
        self.container_instances = {}

    def fetch_task_definition(self, task_definition_str):
        task_definition_str = task_definition_str.split("/")[-1]
        task_definition_components = task_definition_str.split(':')
        if len(task_definition_components) == 2:
            family, revision = task_definition_components
            revision = int(revision)
        else:
            family = task_definition_components[0]
            revision = -1
        if family in self.task_definitions and 0 < revision <= len(self.task_definitions[family]):
            return self.task_definitions[family][revision - 1]
        elif family in self.task_definitions and revision == -1:
            return self.task_definitions[family][revision]
        else:
            raise Exception("{0} is not a task_definition".format(task_definition_str))

    def create_cluster(self, cluster_name):
        cluster = Cluster(cluster_name)
        self.clusters[cluster_name] = cluster
        return cluster

    def list_clusters(self):
        """
        maxSize and pagination not implemented
        """
        return [cluster.arn for cluster in self.clusters.values()]

    def describe_clusters(self, list_clusters_name=None):
        list_clusters = []
        if list_clusters_name is None:
            if 'default' in self.clusters:
                list_clusters.append(self.clusters['default'].response_object)
        else:
            for cluster in list_clusters_name:
                cluster_name = cluster.split('/')[-1]
                if cluster_name in self.clusters:
                    list_clusters.append(self.clusters[cluster_name].response_object)
                else:
                    raise Exception("{0} is not a cluster".format(cluster_name))
        return list_clusters

    def delete_cluster(self, cluster_str):
        cluster_name = cluster_str.split('/')[-1]
        if cluster_name in self.clusters:
            return self.clusters.pop(cluster_name)
        else:
            raise Exception("{0} is not a cluster".format(cluster_name))

    def register_task_definition(self, family, container_definitions, volumes, task_role_arn):
        if family in self.task_definitions:
            revision = len(self.task_definitions[family]) + 1
        else:
            self.task_definitions[family] = []
            revision = 1
        task_definition = TaskDefinition(family, revision, container_definitions, volumes, task_role_arn)
        self.task_definitions[family].append(task_definition)

        return task_definition

    def list_task_definitions(self):
        """
        Filtering not implemented
        """
        task_arns = []
        for task_definition_list in self.task_definitions.values():
            task_arns.extend([task_definition.arn for task_definition in task_definition_list])
        return task_arns

    def deregister_task_definition(self, task_definition_str):
        task_definition_name = task_definition_str.split('/')[-1]
        family, revision = task_definition_name.split(':')
        revision = int(revision)
        if family in self.task_definitions and 0 < revision <= len(self.task_definitions[family]):
            return self.task_definitions[family].pop(revision - 1)
        else:
            raise Exception("{0} is not a task_definition".format(task_definition_name))

    def create_service(self, cluster_str, service_name, task_definition_str, desired_count, role=None, loadBalancers=[]):
        cluster_name = cluster_str.split('/')[-1]
        if cluster_name in self.clusters:
            cluster = self.clusters[cluster_name]
        else:
            raise Exception("{0} is not a cluster".format(cluster_name))
        task_definition = self.fetch_task_definition(task_definition_str)
        desired_count = desired_count if desired_count is not None else 0
        service = Service(cluster, service_name, task_definition, desired_count, role, loadBalancers)
        cluster_service_pair = '{0}:{1}'.format(cluster_name, service_name)
        self.services[cluster_service_pair] = service
        return service

    def describe_task_definition(self, task_definition_name):
        task_definition_name = task_definition_name.split('/')[-1]
        if ":" in task_definition_name:
            family, revision = task_definition_name.split(':')
            revision = int(revision)
        else:
            family = task_definition_name
            revision = len(self.task_definitions[family])
        return self.task_definitions[family][revision - 1]

    def describe_services(self, cluster_str, service_strs):
        cluster_name = cluster_str.split('/')[-1]
        services = []
        for service_str in service_strs:
            service_name = service_str.split('/')[-1]
            for key, value in self.services.items():
                if cluster_name + ':' in key and service_name == value.name:
                    services.append(value.response_object)
        return services

    def list_services(self, cluster_str):
        cluster_name = cluster_str.split('/')[-1]
        service_arns = []
        for key, value in self.services.items():
            if cluster_name + ':' in key:
                service_arns.append(self.services[key].arn)
        return sorted(service_arns)

    def update_service(self, cluster_str, service_name, task_definition_str, desired_count):
        cluster_name = cluster_str.split('/')[-1]
        cluster_service_pair = '{0}:{1}'.format(cluster_name, service_name)
        if cluster_service_pair in self.services:
            if task_definition_str is not None:
                task_definition = self.fetch_task_definition(task_definition_str)
                self.services[cluster_service_pair].task_definition = task_definition.arn
            if desired_count is not None:
                service = self.services[cluster_service_pair]
                service.desired_count = desired_count
                service.running_count = desired_count
                service.deployments[0]["desiredCount"] = desired_count
                service.deployments[0]["runningCount"] = desired_count
            return self.services[cluster_service_pair]
        else:
            raise Exception("cluster {0} or service {1} does not exist".format(cluster_name, service_name))

    def delete_service(self, cluster_name, service_name):
        cluster_service_pair = '{0}:{1}'.format(cluster_name, service_name)
        if cluster_service_pair in self.services:
            service = self.services[cluster_service_pair]
            if service.desired_count > 0:
                raise Exception("Service must have desiredCount=0")
            else:
                service.status = "INACTIVE"
                service.events = []
                service.deployments = []
                service.desired_count = 0
                service.running_count = 0
                service.pending_count = 0
                return service
        else:
            raise Exception("cluster {0} or service {1} does not exist".format(cluster_name, service_name))

    def register_container_instance(self, cluster_str, ec2_instance_id):
        cluster_name = cluster_str.split('/')[-1]
        if cluster_name not in self.clusters:
            raise Exception("{0} is not a cluster".format(cluster_name))
        container_instance = ContainerInstance(ec2_instance_id)
        if not self.container_instances.get(cluster_name):
            self.container_instances[cluster_name] = {}
        container_instance_id = container_instance.containerInstanceArn.split('/')[-1]
        self.container_instances[cluster_name][container_instance_id] = container_instance
        return container_instance

    def list_container_instances(self, cluster_str):
        cluster_name = cluster_str.split('/')[-1]
        container_instances_values = self.container_instances.get(cluster_name, {}).values()
        container_instances = [ci.containerInstanceArn for ci in container_instances_values]
        return sorted(container_instances)

    def describe_container_instances(self, cluster_str, list_container_instance_ids):
        cluster_name = cluster_str.split('/')[-1]
        if cluster_name not in self.clusters:
            raise Exception("{0} is not a cluster".format(cluster_name))
        failures = []
        container_instance_objects = []
        for container_instance_id in list_container_instance_ids:
            container_instance = self.container_instances[cluster_name].get(container_instance_id, None)
            if container_instance is not None:
                container_instance_objects.append(container_instance)
            else:
                failures.append(ContainerInstanceFailure('MISSING', container_instance_id))

        return container_instance_objects, failures

    def deregister_container_instance(self, cluster_str, container_instance_str):
        pass


ecs_backends = {}
for region, ec2_backend in ec2_backends.items():
    ecs_backends[region] = EC2ContainerServiceBackend()
