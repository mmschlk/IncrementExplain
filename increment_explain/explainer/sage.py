"""
This module gathers SAGE Explanation Methods
"""

# Authors: Maximilian Muschalik <maximilian.muschalik@lmu.de>
#          Fabian Fumagalli <ffumagalli@techfak.uni-bielefeld.de>

import copy
from abc import ABCMeta
from abc import abstractmethod

import numpy as np

from storage.sampler import BatchSampler, ReservoirSampler, HistogramSampler
from utils.trackers import WelfordTracker, ExponentialSmoothingTracker

__all__ = [
    "IncrementalSAGE",
]

# =============================================================================
# Types and constants
# =============================================================================

EPS = 1e-10

# TODO change MAE and MSE loss to be used with arrays
def mae_loss(y_true, y_prediction):
    return abs(y_true - y_prediction)


def mse_loss(y_true, y_prediction):
    return (y_true - y_prediction) ** 2


# =============================================================================
# Base Sampler Class
# =============================================================================


class BaseIncrementalExplainer(metaclass=ABCMeta):
    """Base class for incremental explainer algorithms.

    Warning: This class should not be used directly.
    Use derived classes instead.
    """

    @abstractmethod
    def __init__(
            self,
            *,
            model_fn,
            feature_names,
            random_state
    ):
        self.model_fn = model_fn
        self.feature_names = feature_names
        self.random_state = random_state
        self.number_of_features = len(feature_names)
        self.seen_samples = 0

    @abstractmethod
    def explain_one(self, x, y):
        pass


# =============================================================================
# Public SAGE Explainers
# =============================================================================


class IncrementalSAGE(BaseIncrementalExplainer):

    def __init__(
            self,
            model_fn,
            *,
            feature_names,
            loss_function='mse',
            random_state=None,
            sub_sample_size=1,
            empty_prediction=None,
            default_values: list = None
    ):
        super(IncrementalSAGE, self).__init__(
            model_fn=model_fn,
            feature_names=feature_names,
            random_state=random_state
        )
        # TODO enable custom loss functions as parameters
        assert loss_function in ['mae', 'mse'], "Loss function must be either 'mae' or 'mse'."
        if loss_function == 'mae':
            self.loss_function = mae_loss
        else:
            self.loss_function = mse_loss
        self.default_values = default_values
        if default_values is None:
            self.sampler = ReservoirSampler(feature_names=feature_names,
                                            constant_probability=1.,
                                            store_targets=False,
                                            reservoir_length=300,
                                            sample_with_replacement=False)
        else:
            self.default_values = {feature: default_values[i] for feature, i in zip(feature_names, range(len(feature_names)))}
        self.sub_sample_size = sub_sample_size
        self.marginal_prediction = ExponentialSmoothingTracker(alpha=0.005)
        self.SAGE_trackers = {feature_name: ExponentialSmoothingTracker(alpha=0.005) for feature_name in feature_names}
        self.pfi_trackers = {feature_name: ExponentialSmoothingTracker(alpha=0.005) for feature_name in feature_names}

    @property
    def SAGE_values(self):
        return {feature_name: float(self.SAGE_trackers[feature_name].tracked_value) for feature_name in self.feature_names}

    def _update_sampler(self, x, y):
        self.sampler.update(x, y)

    def explain_one(self, x_i, y_i):
        if self.seen_samples < 1:  # TODO remove warmup-phase
            self.seen_samples += 1
            if self.default_values is None:
                self._update_sampler(x_i, y_i)
            return self.SAGE_values
        permutation_chain = np.random.permutation(self.feature_names)
        if self.default_values is None:
            x_marginal, _ = self.sampler.sample(k=1)
        else:
            x_marginal = [self.default_values]
        marginal_prediction = self.model_fn(x_marginal[0])[0]
        self.marginal_prediction.update(marginal_prediction)
        sample_loss = self.loss_function(y_true=y_i, y_prediction=self.marginal_prediction())
        x_S = {}
        for feature in permutation_chain:
            x_S[feature] = x_i[feature]
            y = 0
            if self.default_values is None:
                x_marginals, _ = self.sampler.sample(k=self.sub_sample_size)
            else:
                x_marginals = [self.default_values for _ in range(self.sub_sample_size)]
            k = 0
            while k < min(self.sub_sample_size, len(x_marginals)):
                x_marginal = {**x_marginals[k], **x_S}
                y += self.model_fn(x_marginal)[0]
                k += 1
            y /= k
            feature_loss = self.loss_function(y_true=y_i, y_prediction=y)
            marginal_contribution = sample_loss - feature_loss
            self.SAGE_trackers[feature].update(marginal_contribution)
            sample_loss = feature_loss
        self.seen_samples += 1
        if self.default_values is None:
            self._update_sampler(x_i, y_i)
        return self.SAGE_values
