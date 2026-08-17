"""Reusable input montages for common competitive Melee techniques."""

from melee.bot.techskill.common import WavedashDirection
from melee.bot.techskill.ledgedash import LedgedashMontage
from melee.bot.techskill.multishine import MultishineMontage
from melee.bot.techskill.sdi import SDIMontage
from melee.bot.techskill.wavedash import WavedashMontage

__all__ = [
    "LedgedashMontage",
    "MultishineMontage",
    "SDIMontage",
    "WavedashDirection",
    "WavedashMontage",
]
