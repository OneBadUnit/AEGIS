# sources/base.py

from abc import ABC, abstractmethod
from typing import List

from models import RawPost


class BaseCollector(ABC):
    """
    Base class for all data collectors in our project.

    Purpose:
    - Enforce a consistent interface across all sources
      (Reddit, Hacker News, GitHub, etc.)
    - Guarantee that every collector returns standardized RawPost objects
    - Make it easy to plug new sources into the pipeline without changes elsewhere

    Contract:
    - Every collector MUST implement `fetch()`
    - `fetch()` MUST return a List[RawPost]
    """

    @abstractmethod
    def fetch(self) -> List[RawPost]:
        """
        Fetch data from the source and return a list of RawPost objects.

        Rules:
        - Must return a list (never None)
        - Must only return valid RawPost objects
        - Should filter low-quality / noisy data before returning
        - Should handle its own errors and avoid crashing the pipeline

        Returns:
            List[RawPost]
        """
        raise NotImplementedError("Collectors must implement fetch()")