from abc import abstractmethod, ABC
from typing import Callable


class BaseImputer(ABC):
    """Base class for sampling algorithms.

    Warning: This class should not be used directly.
    Use derived classes instead.
    """

    @abstractmethod
    def __init__(
            self,
            model_function: Callable
    ):
        self.model_function = model_function

    @abstractmethod
    def impute(self, feature_subset, x_i, n_samples=None):
        raise NotImplementedError
