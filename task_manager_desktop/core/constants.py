"""Constantes canonicas compartilhadas pelo task-manager-desktop.

Mantenha aqui apenas valores cuja mudanca afeta multiplos modulos. Para
constantes locais de um unico arquivo, prefira definir no proprio modulo.
"""

from __future__ import annotations

# Acima deste limite, ChangeStatusController dispara refresh global em vez de
# mover cards um a um. Move atomico se < THRESHOLD; refresh em lote acima.
PROPAGATION_THRESHOLD: int = 20
