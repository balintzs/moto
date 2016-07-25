from __future__ import unicode_literals
import json
import hashlib

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


class Repository(BaseObject):
    def __init__(self, repo_name):
        self.registry_id = "012345678910"
        self.repository_arn = 'arn:aws:ecr:us-east-1:{}:repository/{}'.format(self.registry_id, repo_name)
        self.repository_name = repo_name
        self.repository_uri = "{}.dkr.ecr.us-east-1.amazonaws.com/{}".format(self.registry_id, repo_name)
        self.images = {}

    @property
    def response_object(self):
        obj = self.gen_response_object()
        obj.pop("images")
        return obj


class Image(BaseObject):
    def __init__(self, registry_id, repository_name, manifest):
        self.registry_id = manifest
        self.repository_name = repository_name
        self.image_manifest = manifest
        self.image_id = dict(
            imageDigest=hashlib.sha256(manifest.encode()).hexdigest(),
            imageTag=json.loads(manifest)["tag"]
        )


class ECSContainerRegistryBackend(BaseBackend):
    def __init__(self):
        self.repositories = {}

    def create_repository(self, name):
        repo = Repository(name)
        self.repositories[name] = repo
        return repo

    def describe_repositories(self, registry_id, repository_names):
        """
        maxResults and pagination not implemented
        """
        return [
            self.repositories[repo].response_object for repo in repository_names
        ]

    def delete_repository(self, registry_id, repository_name):
        return self.repositories.pop(repository_name)

    def put_image(self, registry_id, repository_name, image_manifest):
        image = Image(registry_id, repository_name, image_manifest)
        self.repositories[repository_name].images[image.image_id["imageTag"]] = image
        return image.response_object

    def list_images(self, registry_id, repository_name):
        """
        maxResults and pagination not implemented
        """
        repo = self.repositories[repository_name]
        return [
            repo.images[tag].image_id
            for tag in repo.images
        ]

    def batch_get_image(self, registry_id, repository_name, image_ids):
        """
        maxResults and pagination not implemented
        """
        repo = self.repositories[repository_name]
        return dict(
            images=[
                repo.images[image_id["imageTag"]].response_object
                for image_id in image_ids
                if image_id["imageTag"] in repo.images
            ],
            failures=[
                dict(
                    imageId=image_id,
                    failureCode="InvalidImageTag",
                    failureReason="Tag not found"
                )
                for image_id in image_ids
                if image_id["imageTag"] not in repo.images
            ]
        )

    def batch_delete_image(self, registry_id, repository_name, image_ids):
        """
        maxResults and pagination not implemented
        """
        repo = self.repositories[repository_name]
        deleted = []
        failed = []
        for image_id in image_ids:
            if image_id["imageTag"] in repo.images:
                deleted.append(repo.images.pop(image_id["imageTag"]).response_object)
            else:
                failed.append(dict(
                    imageId=image_id,
                    failureCode="InvalidImageTag",
                    failureReason="Tag not found"
                ))
        return dict(
            imageIds=deleted,
            failures=failed
        )


ecr_backends = {}
for region, ec2_backend in ec2_backends.items():
    ecr_backends[region] = ECSContainerRegistryBackend()
