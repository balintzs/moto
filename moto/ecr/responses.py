from __future__ import unicode_literals
import json

from moto.core.responses import BaseResponse
from .models import ecr_backends


class ECSContainerRegistryResponse(BaseResponse):
    @property
    def ecr_backend(self):
        return ecr_backends[self.region]

    @property
    def request_params(self):
        try:
            return json.loads(self.body.decode())
        except ValueError:
            return {}

    def _get_param(self, param):
        return self.request_params.get(param, None)

    def create_repository(self):
        repository = self.ecr_backend.create_repository(
            self._get_param('repositoryName')
        )
        return json.dumps({
            'repository': repository.response_object
        })

    def describe_repositories(self):
        repositories = self.ecr_backend.list_clusters(
            self._get_param("registryId"),
            self._get_param("repositoryNames")
        )
        return json.dumps({
            'repositories': repositories
        })

    def delete_repository(self):
        repository = self.ecr_backend.list_clusters(
            self._get_param("registryId"),
            self._get_param("repositoryName")
        )
        return json.dumps({
            'repository': repository
        })

    def put_image(self):
        image = self.ecr_backend.put_image(
            self._get_param("registryId"),
            self._get_param("repositoryName"),
            self._get_param("imageManifest")
        )
        return json.dumps({
            'image': image
        })

    def list_images(self):
        images = self.ecr_backend.list_images(
            self._get_param("registryId"),
            self._get_param("repositoryName")
        )
        return json.dumps({
            'imageIds': images
        })

    def batch_get_image(self):
        results = self.ecr_backend.batch_get_image(
            self._get_param("registryId"),
            self._get_param("repositoryName"),
            self._get_param("imageIds")
        )
        return json.dumps(results)

    def batch_delete_image(self):
        results = self.ecr_backend.batch_delete_image(
            self._get_param("registryId"),
            self._get_param("repositoryName"),
            self._get_param("imageIds")
        )
        return json.dumps(results)
