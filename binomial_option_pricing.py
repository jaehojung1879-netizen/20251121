"""Simple binomial option pricing model implementation.

This module provides a straightforward binomial tree pricer for European and
American call/put options using the Cox-Ross-Rubinstein formulation.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

OptionType = Literal["call", "put"]


def _validate_inputs(spot: float, strike: float, maturity: float, rate: float, steps: int, up: float, down: float) -> None:
    if spot <= 0:
        raise ValueError("Spot price must be positive")
    if strike <= 0:
        raise ValueError("Strike price must be positive")
    if maturity <= 0:
        raise ValueError("Maturity must be positive")
    if steps <= 0:
        raise ValueError("Steps must be positive")
    if up <= 0 or down <= 0:
        raise ValueError("Up and down factors must be positive")
    if up <= down:
        raise ValueError("Up factor must exceed down factor")
    if down >= math.exp(rate * (maturity / steps)):
        raise ValueError("Down factor must be less than the discount factor to avoid arbitrage")


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
class BinomialOptionResult:
    """Result of the binomial pricing routine."""

    price: float
    delta: float


def binomial_option_price(
    spot: float,
    strike: float,
    maturity: float,
    rate: float,
    up: float,
    down: float,
    steps: int,
    option_type: OptionType = "call",
    american: bool = False,
) -> BinomialOptionResult:
    """Price an option using the Cox-Ross-Rubinstein binomial tree.

    Args:
        spot: Current underlying asset price.
        strike: Option strike price.
        maturity: Time to maturity (in years).
        rate: Continuously compounded risk-free rate.
        up: Upward movement factor per step.
        down: Downward movement factor per step.
        steps: Number of binomial steps.
        option_type: "call" or "put".
        american: If True, compute the American option price; otherwise European.

    Returns:
        BinomialOptionResult with price and delta.
    """
    _validate_inputs(spot, strike, maturity, rate, steps, up, down)

    dt = maturity / steps
    discount = math.exp(-rate * dt)
    p = (math.exp(rate * dt) - down) / (up - down)
    if not 0 <= p <= 1:
        raise ValueError("Risk-neutral probability out of bounds; check parameters")

    # Initialize terminal payoffs
    prices = [spot * (up ** j) * (down ** (steps - j)) for j in range(steps + 1)]
    values = [payoff(price, strike, option_type) for price in prices]

    # Backward induction
    for step in range(steps - 1, -1, -1):
        for i in range(step + 1):
            continuation = discount * (p * values[i + 1] + (1 - p) * values[i])
            if american:
                current_price = spot * (up ** i) * (down ** (step - i))
                exercise = payoff(current_price, strike, option_type)
                values[i] = max(continuation, exercise)
            else:
                values[i] = continuation

    # Delta from first step prices
    delta = (values[1] - values[0]) / (spot * (up - down))
    return BinomialOptionResult(price=values[0], delta=delta)


if __name__ == "__main__":
    # Example usage
    result = binomial_option_price(
        spot=100,
        strike=100,
        maturity=1.0,
        rate=0.05,
        up=1.1,
        down=0.9,
        steps=3,
        option_type="call",
        american=False,
    )
    print(f"Option price: {result.price:.4f}, Delta: {result.delta:.4f}")
