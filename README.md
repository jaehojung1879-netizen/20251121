# Option Pricing Tools

This repository bundles two lightweight pricing utilities:

- **Binomial (Cox-Ross-Rubinstein) pricer** for European and American calls/puts with delta estimation.
- **Monte Carlo GBM pricer** that accepts any custom payoff function and reports the standard error alongside the price.

## Quick start

Run either module directly to execute the built-in examples:

```bash
python binomial_option_pricing.py
python monte_carlo_option_pricing.py
```

## Web-based Monte Carlo option calculator

A lightweight Flask server exposes a form-driven Monte Carlo calculator that accepts custom payoffs. Install the dependency and start the server:

```bash
pip install -r requirements.txt
python web_option_calculator.py --host 0.0.0.0 --port 5000
```

Then open <http://localhost:5000/price> and enter your parameters:

- **Payoff expression:** Python expression using `S` (or `spot`) for the terminal price and `K` (or `strike`) for the strike, e.g. `max(S - K, 0)` for a vanilla call or `max(1 if S > 120 else 0, 0)` for a digital payoff.
- **Paths/steps:** Control simulation fidelity; increasing either reduces variance at additional runtime cost.
- **Seed:** Optional integer to make runs reproducible.

An accompanying JSON API is available at `POST /api/price` with the same fields (`spot`, `strike`, `maturity`, `rate`, `volatility`, `steps`, `paths`, `payoff`, optional `seed`).

## Binomial option pricer

`binomial_option_pricing.py` computes prices using a Cox-Ross-Rubinstein tree. It supports European or American exercise and returns both the option price and an estimated delta.

Key parameters include the underlying spot, strike, maturity, risk-free rate, up/down factors, number of steps, and whether the option is American. Edit the `__main__` block for a quick custom calculation or import `binomial_option_price` from another module.

## Monte Carlo pricer with custom payoff

`monte_carlo_option_pricing.py` simulates geometric Brownian motion paths. You can supply any Python callable as the payoff to model custom contracts (for example, Asian payoffs or digital options). The example in `__main__` shows how to pass a lambda for a vanilla call payoff and how to set a random seed for reproducible runs.
