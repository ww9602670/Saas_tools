"""
模块职能：
- 连接器注册表：site -> ConnectorClass
"""
from typing import Dict, Type
from app.connectors.base import BaseConnector
from app.connectors.example_site.client import ExampleConnector

REGISTRY: Dict[str, Type[BaseConnector]] = {
    "example": ExampleConnector,
}

def get_connector(site: str) -> Type[BaseConnector]:
    return REGISTRY[site]
