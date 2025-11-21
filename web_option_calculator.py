"""Flask app exposing a web form for Monte Carlo option pricing."""
from __future__ import annotations

import argparse
import math
from typing import Callable, Dict

from flask import Flask, jsonify, redirect, render_template_string, request, url_for

from monte_carlo_option_pricing import MonteCarloResult, monte_carlo_option_price


ALLOWED_NAMES: Dict[str, Callable[..., float]] = {
    "abs": abs,
    "max": max,
    "min": min,
    # Common math helpers for convenience in payoff expressions
    "exp": math.exp,
    "log": math.log,
    "sqrt": math.sqrt,
}


def compile_payoff(expression: str, strike: float) -> Callable[[float], float]:
    """Compile a user-supplied payoff expression into a callable.

    The expression may reference:
    - ``S`` or ``spot``: the terminal asset price per simulation path
    - ``K`` or ``strike``: the strike provided in the form
    - Any helper in ``ALLOWED_NAMES`` (e.g., ``max``, ``min``, ``abs``, ``exp``)

    Args:
        expression: Python expression string representing the payoff.
        strike: Strike price to inject as ``K``/``strike``.

    Returns:
        Callable that accepts a terminal price and returns a payoff.
    """
    clean_expression = expression.strip()
    if not clean_expression:
        raise ValueError("Payoff expression cannot be empty")

    compiled = compile(clean_expression, "<payoff>", "eval")

    def payoff_fn(terminal_price: float) -> float:
        scope = {
            "S": terminal_price,
            "spot": terminal_price,
            "K": strike,
            "strike": strike,
            **ALLOWED_NAMES,
        }
        return float(eval(compiled, {"__builtins__": {}}, scope))

    return payoff_fn


def create_app() -> Flask:
    app = Flask(__name__)

    template = """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Monte Carlo Option Calculator</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 1.5rem; }
          form { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; }
          label { display: flex; flex-direction: column; font-weight: bold; }
          input, textarea { margin-top: 0.25rem; padding: 0.35rem; font-size: 1rem; }
          .actions { grid-column: 1 / -1; }
          .result { margin-top: 1rem; padding: 1rem; background: #f5f5f5; border-radius: 4px; }
          .error { color: #b00020; font-weight: bold; }
        </style>
      </head>
      <body>
        <h1>Monte Carlo Option Calculator</h1>
        <form method="post" action="{{ url_for('price') }}">
          <label>Spot price
            <input type="number" step="0.01" name="spot" value="{{ form.spot }}" required>
          </label>
          <label>Strike price
            <input type="number" step="0.01" name="strike" value="{{ form.strike }}" required>
          </label>
          <label>Maturity (years)
            <input type="number" step="0.01" name="maturity" value="{{ form.maturity }}" required>
          </label>
          <label>Risk-free rate (cont., annualized)
            <input type="number" step="0.0001" name="rate" value="{{ form.rate }}" required>
          </label>
          <label>Volatility (annualized)
            <input type="number" step="0.0001" name="volatility" value="{{ form.volatility }}" required>
          </label>
          <label>Time steps per path
            <input type="number" name="steps" value="{{ form.steps }}" required>
          </label>
          <label>Simulation paths
            <input type="number" name="paths" value="{{ form.paths }}" required>
          </label>
          <label>Random seed (optional)
            <input type="number" name="seed" value="{{ form.seed }}">
          </label>
          <label class="actions">Payoff expression (Python)
            <textarea name="payoff" rows="3" required>{{ form.payoff }}</textarea>
            <small>Use S (or spot) for the terminal price and K (or strike) for the strike. Example: max(S - K, 0)</small>
          </label>
          <div class="actions">
            <button type="submit">Price option</button>
          </div>
        </form>

        {% if error %}
          <div class="result error">{{ error }}</div>
        {% endif %}

        {% if result %}
          <div class="result">
            <div><strong>Price:</strong> {{ result.price }}</div>
            <div><strong>Standard error:</strong> {{ result.standard_error }}</div>
          </div>
        {% endif %}
      </body>
    </html>
    """

    def parse_float(field: str, default: float | None = None) -> float:
        raw = request.form.get(field)
        if raw is None or raw == "":
            if default is None:
                raise ValueError(f"Missing required field: {field}")
            return default
        return float(raw)

    def parse_int(field: str, default: int | None = None) -> int:
        raw = request.form.get(field)
        if raw is None or raw == "":
            if default is None:
                raise ValueError(f"Missing required field: {field}")
            return default
        return int(raw)

    @app.route("/", methods=["GET"])
    def index() -> str:
        return redirect(url_for("price"))

    @app.route("/price", methods=["GET", "POST"])
    def price():
        default_form = {
            "spot": "100",
            "strike": "100",
            "maturity": "1.0",
            "rate": "0.05",
            "volatility": "0.2",
            "steps": "252",
            "paths": "10000",
            "seed": "42",
            "payoff": "max(S - K, 0)",
        }
        if request.method == "GET":
            return render_template_string(template, form=default_form, result=None, error=None)

        try:
            spot = parse_float("spot")
            strike = parse_float("strike")
            maturity = parse_float("maturity")
            rate = parse_float("rate")
            volatility = parse_float("volatility")
            steps = parse_int("steps")
            paths = parse_int("paths")
            seed_raw = request.form.get("seed")
            seed = int(seed_raw) if seed_raw else None
            payoff_expression = request.form.get("payoff", "")

            payoff_fn = compile_payoff(payoff_expression, strike=strike)
            mc_result: MonteCarloResult = monte_carlo_option_price(
                spot=spot,
                maturity=maturity,
                rate=rate,
                volatility=volatility,
                steps=steps,
                paths=paths,
                payoff_fn=payoff_fn,
                seed=seed,
            )

            result_payload = {
                "price": round(mc_result.price, 6),
                "standard_error": round(mc_result.standard_error, 6),
            }
            return render_template_string(
                template, form=request.form, result=result_payload, error=None
            )
        except Exception as exc:  # Flask will still log the stack trace
            error_message = f"Error: {exc}"
            return render_template_string(
                template, form=request.form or default_form, result=None, error=error_message
            )

    @app.route("/api/price", methods=["POST"])
    def price_api():
        try:
            data = request.get_json(force=True)
            payoff_expression = data.get("payoff", "")
            payoff_fn = compile_payoff(payoff_expression, strike=float(data["strike"]))
            mc_result = monte_carlo_option_price(
                spot=float(data["spot"]),
                maturity=float(data["maturity"]),
                rate=float(data["rate"]),
                volatility=float(data["volatility"]),
                steps=int(data["steps"]),
                paths=int(data["paths"]),
                payoff_fn=payoff_fn,
                seed=(int(data["seed"]) if data.get("seed") else None),
            )
            return jsonify(
                {
                    "price": mc_result.price,
                    "standard_error": mc_result.standard_error,
                }
            )
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Monte Carlo option pricing web server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")
    args = parser.parse_args()

    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
