from __future__ import unicode_literals
from .responses import ECSContainerRegistryResponse

url_bases = [
    "https?://ecr.(.+).amazonaws.com",
]

url_paths = {
    '{0}/$': ECSContainerRegistryResponse.dispatch,
}
