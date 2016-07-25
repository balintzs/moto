from __future__ import unicode_literals
from .models import ecr_backends
from ..core.models import MockAWS

ecr_backend = ecr_backends['us-east-1']


def mock_ecr(func=None):
    if func:
        return MockAWS(ecr_backends)(func)
    else:
        return MockAWS(ecr_backends)
