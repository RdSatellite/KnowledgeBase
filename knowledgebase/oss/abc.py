"""
OSS Contract

In our system. We use oss to store the source truth.

We have planned a very special feature here:
    - .any -> .md projection
This will be useful in our RAG system.
    
Some feature can be also added into this component:
    - Slice
    - Zip
"""

from abc import ABC, abstractmethod
from typing import BinaryIO


class ObjectStore(ABC):
    """
    Interface for URI-Object mapping.
    Responsible for managing storage resources and providing URIs.
    """

    @abstractmethod
    def put(self, data: BinaryIO) -> str:
        """
        Persists the object stream and returns its unique absolute URI

        :param data: The binary stream of the object.
        :return: The full storage URI (e.g. 'file:///data/oss/img.png')
        """
        ...

    @abstractmethod
    def get(self, uri: str) -> BinaryIO:
        """
        Retrieve the object stream associated with the given URI.
        
        :param uri: The absolute storage URI.
        :return: A binary stream of the object data.
        """
        ...

    @abstractmethod
    def delete(self, uri: str) -> None:
        """
        Removes the object from the source using its URI.

        :param uri: The absolute storage URI.
        """
        ...
