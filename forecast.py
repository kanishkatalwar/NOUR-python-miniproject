"""AI use case: blood demand forecasting (healthcare).

The first version uses exponential smoothing, a simple statistical model that learns from
past weekly demand and weights recent weeks more. It is a starting point you can later
replace with a trained ML model (for example linear regression or an LSTM) without
changing the rest of NOUR, because the rest of the program only calls forecast_all().

    forecast_t+1 = alpha * actual_t + (1 - alpha) * forecast_t

A higher alpha reacts faster to recent weeks. A lower alpha gives a smoother forecast.
"""
import random

from compatibility import GROUPS

# Typical units issued per week for each group, used to make sample history.
BASE_DEMAND = {"O+": 12, "A+": 9, "B+": 8, "O-": 5, "A-": 3, "B-": 2.5, "AB+": 3, "AB-": 1}


def sample_weekly_history(weeks=8, seed=7):
    """Deterministic sample of units issued per week for every group."""
    rng = random.Random(seed)
    return {g: [round(BASE_DEMAND[g] * (0.75 + rng.random() * 0.5), 1) for _ in range(weeks)]
            for g in GROUPS}


def exponential_smoothing(history, alpha=0.4):
    """Forecast for the next week from a list of past weekly demand."""
    if not history:
        raise ValueError("Need at least one week of history.")
    level = history[0]
    for actual in history[1:]:
        level = alpha * actual + (1 - alpha) * level
    return level


def moving_average(history, window=3):
    recent = history[-window:]
    return sum(recent) / len(recent)


def backtest_mae(history, alpha=0.4):
    """Mean absolute error of one-step-ahead forecasts. Lower is better."""
    if len(history) < 2:
        return 0.0
    level, errors = history[0], []
    for actual in history[1:]:
        errors.append(abs(actual - level))
        level = alpha * actual + (1 - alpha) * level
    return sum(errors) / len(errors)


def forecast_all(history=None, alpha=0.4):
    history = history or sample_weekly_history()
    return {g: round(exponential_smoothing(history[g], alpha), 1) for g in GROUPS}


def coverage_days(units_in_stock, weekly_forecast):
    """How many days the current stock lasts at the forecast rate."""
    if weekly_forecast <= 0:
        return float("inf")
    return units_in_stock / weekly_forecast * 7