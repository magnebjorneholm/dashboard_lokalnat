"""
Intäktsram producers
"""

from .effektiviseringskrav import produce_effektiviseringskrav
from .intaktsram_assembly import assemble_intaktsram

__all__ = [
    'produce_effektiviseringskrav',
    'assemble_intaktsram'
]