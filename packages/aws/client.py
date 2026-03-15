"""Placeholder AWS client factory. Full integration TBD."""

from typing import Any, Optional

import boto3
from botocore.config import Config

from packages.core.config import get_settings


def get_aws_client(
    service_name: str,
    region_name: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    """
    Return a boto3 client for the given service.
    Placeholder: uses env/default credentials. Full logic TBD.
    """
    settings = get_settings()
    region = region_name or settings.aws_region or "us-east-1"
    return boto3.client(
        service_name,
        region_name=region,
        config=Config(retries={"mode": "standard", "max_attempts": 3}),
        **kwargs,
    )


def get_cost_explorer_client():
    """Placeholder: AWS Cost Explorer client."""
    return get_aws_client("ce")


def get_eks_client(region_name: Optional[str] = None):
    """Placeholder: EKS client for Kubernetes cost analysis."""
    return get_aws_client("eks", region_name=region_name)


def get_ec2_client(region_name: Optional[str] = None):
    """Placeholder: EC2 client for waste detection (EBS, ENIs, etc.)."""
    return get_aws_client("ec2", region_name=region_name)


def get_cloudwatch_client(region_name: Optional[str] = None):
    """Placeholder: CloudWatch client for metrics."""
    return get_aws_client("cloudwatch", region_name=region_name)
