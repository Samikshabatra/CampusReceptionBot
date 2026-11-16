"""Reproducibility helpers."""

import random

import numpy as np


def set_seed(seed: int) -> None:
    """Seed Python and NumPy RNGs.

    Args:
        seed: Seed value.
    """
    random.seed(seed)
    np.random.seed(seed)
