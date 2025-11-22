from __future__ import annotations

from typing import Optional


class RiskError(Exception):
    """Errores relacionados con el cálculo del tamaño de posición."""


def compute_position_size(
    balance: float,
    risk_perc: float,
    entry_price: float,
    stop_loss: float,
) -> float:
    """Calcula la cantidad máxima en contratos/monedas según el % de riesgo."""
    if balance <= 0:
        raise RiskError("El balance debe ser positivo.")
    if risk_perc <= 0:
        raise RiskError("El riesgo por operación debe ser mayor a cero.")

    distance = abs(entry_price - stop_loss)
    if distance <= 0:
        raise RiskError("La distancia al stop loss no puede ser cero.")

    risk_amount = balance * risk_perc
    qty = risk_amount / distance
    if qty <= 0:
        raise RiskError("La cantidad calculada es inválida.")
    return qty
