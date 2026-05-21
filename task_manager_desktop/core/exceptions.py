from __future__ import annotations


class TaskNotFoundError(Exception):
    """Levantada quando uma task não é encontrada no banco de dados."""


class MigrationError(Exception):
    """Levantada quando uma migração de schema falha.

    Sinaliza que a inicialização do app deve abortar. Não deve ser
    recapturada para retry em loop: o banco fica em estado conhecido
    (transação revertida via ROLLBACK) e exige intervenção manual,
    tipicamente a restauração do backup gerado antes do ALTER.
    """
