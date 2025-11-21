"""Monte Carlo option pricing under geometric Brownian motion.

This module exposes a flexible simulation-based pricer that accepts user-supplied
payoffs and reports the estimated price with a standard error.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Callable, Literal

OptionType = Literal["call", "put"]


def payoff(price: float, strike: float, option_type: OptionType) -> float:
    """Return option payoff for a call or put.

    Args:
        price: Underlying asset price.
        strike: Strike price.
        option_type: Either "call" or "put".
    """
    if option_type == "call":
        return max(price - strike, 0.0)
    if option_type == "put":
        return max(strike - price, 0.0)
    raise ValueError("option_type must be 'call' or 'put'")


@dataclass
class MonteCarloResult:
    """Result of the Monte Carlo pricing routine."""

    price: float
    standard_error: float


def _validate_inputs(
    spot: float,
    maturity: float,
    rate: float,
    volatility: float,
    steps: int,
    paths: int,
) -> None:
    if spot <= 0:
        raise ValueError("Spot price must be positive")
    if maturity <= 0:
        raise ValueError("Maturity must be positive")
    if volatility < 0:
        raise ValueError("Volatility cannot be negative")
    if steps <= 0:
        raise ValueError("Steps must be positive")
    if paths <= 0:
        raise ValueError("Number of paths must be positive")


def monte_carlo_option_price(
    spot: float,
    maturity: float,
    rate: float,
    volatility: float,
    steps: int,
    paths: int,
    payoff_fn: Callable[[float], float],
    seed: int | None = None,
) -> MonteCarloResult:
    """Estimate an option price with Monte Carlo simulation under GBM dynamics.

    Args:
        spot: Current underlying asset price.
        maturity: Time to maturity (in years).
        rate: Continuously compounded risk-free rate.
        volatility: Annualized volatility of the underlying.
        steps: Number of timesteps in each simulated path.
        paths: Number of Monte Carlo simulation paths.
        payoff_fn: Callable that accepts a simulated terminal price and returns a payoff.
        seed: Optional random seed for reproducibility.

    Returns:
        MonteCarloResult with the estimated price and standard error of the mean.
    """
    _validate_inputs(spot, maturity, rate, volatility, steps, paths)

    rng = random.Random(seed)
    dt = maturity / steps
    drift = (rate - 0.5 * volatility**2) * dt
    diffusion = volatility * math.sqrt(dt)

    discounted_payoffs = []
    for _ in range(paths):
        price_path = spot
        for _ in range(steps):
            z = rng.gauss(0.0, 1.0)
            price_path *= math.exp(drift + diffusion * z)
        discounted_payoffs.append(math.exp(-rate * maturity) * payoff_fn(price_path))

    mean_payoff = sum(discounted_payoffs) / paths
    if paths > 1:
        variance = sum((p - mean_payoff) ** 2 for p in discounted_payoffs) / (paths - 1)
        standard_error = math.sqrt(variance / paths)
    else:
        standard_error = float("nan")

    return MonteCarloResult(price=mean_payoff, standard_error=standard_error)


if __name__ == "__main__":
    # Monte Carlo example with a user-defined payoff (European call)
    mc_result = monte_carlo_option_price(
        spot=100,
        maturity=1.0,
        rate=0.05,
        volatility=0.2,
        steps=252,
        paths=10_000,
        payoff_fn=lambda terminal_price: payoff(terminal_price, strike=100, option_type="call"),
        seed=42,
    )
    print(
        f"Monte Carlo price: {mc_result.price:.4f}"
        f" (std error: {mc_result.standard_error:.4f})"
    )
