from typing import List, Dict, Optional, Any
from abc import abstractmethod, ABC


class BaseStorage(ABC):
    """Base class for sampling algorithms.

    Warning: This class should not be used directly.
    Use derived classes instead.
    """
    @abstractmethod
    def __init__(self):
        self._storage_x: List[Dict[str, Any]] = []
        self._storage_y: List = []

    @abstractmethod
    def update(self, x: Dict, y: Optional[Any]):
        """Given a data point, it updates the storage.

        Args:
            x: Features as List of Dicts
            y: Target as float or integer
            
        Returns:
            None
        """
        raise NotImplementedError

    def __len__(self):
        """Returns size of storage object

        Returns:
            Number of objects in storage.
        """
        return len(self._storage_x)

    def get_data(self):
        """Fetches data from storage.

        Returns:
            List of Features and targets in storage as tuple.
        """
        return (self._storage_x, self._storage_y)
