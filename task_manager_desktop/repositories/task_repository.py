from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from task_manager_desktop.core.exceptions import TaskNotFoundError
from task_manager_desktop.core.models import (
    Status,
    Subtask,
    Task,
    TaskType,
    parse_deps,
)

# Valores canonicos aceitos em cada coluna enumerada de `tasks` ao LER do banco.
# Usado por _row_to_task para fail-fast explicito quando o banco esta corrompido
# (valor fora do dominio) em vez de estourar um erro opaco de Status()/TaskType().
_VALID_STATUS = {s.value for s in Status}
_VALID_TYPE = {t.value for t in TaskType}


class SubtaskNotFoundError(Exception):
    """Levantada quando uma subtask nao e encontrada no banco de dados.

    Equivalente a TaskNotFoundError para a tabela `subtasks`: sinaliza que um
    UPDATE pontual nao afetou nenhuma linha (rowcount == 0), evitando que o
    caller trate uma escrita perdida como sucesso.
    """


class DataCorruptionError(Exception):
    """Levantada quando uma linha do banco tem valor fora do dominio esperado.

    Diferente de uma falha de I/O: o banco esta acessivel, mas uma coluna
    enumerada (status, type, favorito, permanente) contem um valor que nenhuma
    versao valida do schema produziria. Nomeia o `task_id` e a coluna ofensora
    para diagnostico rapido. Fail-fast e explicito - nunca silenciar nem coagir.
    """


@dataclass(frozen=True)
class HideAllDoneResult:
    """Resultado estruturado de `hide_all_done()` (source.md secao 9).

    Campos:
        affected_count: numero de tasks DONE nao-permanentes efetivamente
            ocultadas (hidden_at preenchido) por esta chamada.
        excluded_permanente_count: numero de tasks DONE permanentes ainda
            visiveis que a vassoura deliberadamente NAO ocultou.

    Compativel com `int` por design: `__eq__`, `__int__`, `__index__` e
    `__bool__` espelham `affected_count`, de modo que `repo.hide_all_done() == 3`,
    `if repo.hide_all_done():` e `repo.hide_all_done() > 0` continuam validos
    para callers legados que tratavam o retorno como contagem simples.
    """

    affected_count: int
    excluded_permanente_count: int

    def __int__(self) -> int:
        return self.affected_count

    def __index__(self) -> int:
        return self.affected_count

    def __bool__(self) -> bool:
        return self.affected_count != 0

    def __eq__(self, other: object) -> bool:
        if isinstance(other, HideAllDoneResult):
            return (
                self.affected_count == other.affected_count
                and self.excluded_permanente_count == other.excluded_permanente_count
            )
        if isinstance(other, int):
            return self.affected_count == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.affected_count, self.excluded_permanente_count))

    def __gt__(self, other: object) -> bool:
        if isinstance(other, int):
            return self.affected_count > other
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, int):
            return self.affected_count < other
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, int):
            return self.affected_count >= other
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, int):
            return self.affected_count <= other
        return NotImplemented


def _flag_to_int(value: bool, field_name: str) -> int:
    """Converte um flag booleano para 0/1 para persistencia em coluna INTEGER.

    Rejeita explicitamente qualquer valor que nao seja True/False (ex.: int
    fora de {0, 1}, str, None vindos de um bug no caller) levantando ValueError
    em vez de coagir silenciosamente - o erro de constraint nao e escondido.
    """
    if not isinstance(value, bool):
        raise ValueError(
            f"{field_name} deve ser booleano (True ou False); "
            f"recebido {value!r} do tipo {type(value).__name__}"
        )
    return int(value)


def _validate_order_index(value: object) -> int:
    """Valida um `order_index` no boundary de escrita.

    source.md secao 0 / invariante 9: `order_index` participa do contrato de
    ordenacao `(favorito DESC, order_index ASC, id ASC)`; valores negativos nao
    tem significado e seriam um bug silencioso de caller. Rejeita qualquer coisa
    que nao seja um inteiro >= 0 com ValueError explicito (bool e rejeitado de
    proposito - True/False nunca e um indice de ordenacao valido).
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"order_index deve ser inteiro >= 0; recebido {value!r} "
            f"do tipo {type(value).__name__}"
        )
    if value < 0:
        raise ValueError(f"order_index deve ser >= 0; recebido {value}")
    return value


def _enforce_single_row(rowcount: int, row_id: object, op: str) -> None:
    """Aplica o contrato de UPDATE de linha unica por `id`.

    source.md secao 3.4 / invariante 8: um UPDATE pontual por `id` deve afetar
    exatamente uma linha. `rowcount == 0` significa que a task sumiu (corrida)
    e o caller NAO pode tratar como sucesso -> TaskNotFoundError. `rowcount > 1`
    significa `id` duplicado, violando a unicidade da PK -> IntegrityError.
    """
    if rowcount == 0:
        raise TaskNotFoundError(f"Task {row_id!r} não encontrada")
    if rowcount > 1:
        raise sqlite3.IntegrityError(
            f"{op} afetou {rowcount} linhas para id {row_id!r}; "
            "a coluna id deveria ser unica"
        )


def _normalize_enum(
    raw: object, valid: set[str], column: str, task_id: object
) -> str:
    """Normaliza um valor de coluna enumerada lido do banco.

    Aceita variacoes toleraveis (espacos nas pontas, caixa alta de um valor
    canonico) coagindo para o valor canonico; rejeita qualquer outra coisa
    (NULL, string desconhecida) com DataCorruptionError nomeando task_id e
    coluna. Nunca silencia: um valor genuinamente invalido aborta o load.
    """
    if raw is None:
        raise DataCorruptionError(
            f"task {task_id!r}: coluna '{column}' e NULL; "
            f"esperado um de {sorted(valid)}"
        )
    if not isinstance(raw, str):
        raise DataCorruptionError(
            f"task {task_id!r}: coluna '{column}' tem tipo "
            f"{type(raw).__name__} ({raw!r}); esperado texto"
        )
    candidate = raw.strip().lower()
    if candidate in valid:
        return candidate
    raise DataCorruptionError(
        f"task {task_id!r}: coluna '{column}' tem valor {raw!r}; "
        f"esperado um de {sorted(valid)}"
    )


def _normalize_flag(raw: object, column: str, task_id: object) -> bool:
    """Normaliza uma coluna booleana (favorito|permanente) lida do banco.

    Aceita 0/1 (INTEGER canonico), None (-> False, linha pre-v7) e os textos
    '0'/'1' por tolerancia. Qualquer outro valor (ex.: 'yes', 2, 'true')
    levanta DataCorruptionError em vez de coagir silenciosamente.
    """
    if raw is None:
        return False
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, int):
        if raw in (0, 1):
            return bool(raw)
        raise DataCorruptionError(
            f"task {task_id!r}: coluna '{column}' tem valor {raw!r}; "
            "esperado 0 ou 1"
        )
    if isinstance(raw, str):
        candidate = raw.strip()
        if candidate in ("0", "1"):
            return candidate == "1"
        raise DataCorruptionError(
            f"task {task_id!r}: coluna '{column}' tem valor {raw!r}; "
            "esperado 0 ou 1"
        )
    raise DataCorruptionError(
        f"task {task_id!r}: coluna '{column}' tem tipo "
        f"{type(raw).__name__} ({raw!r}); esperado 0 ou 1"
    )


def _row_to_task(row: sqlite3.Row) -> Task:
    """Mapeia uma linha de `tasks` para Task, validando o dominio das colunas.

    Colunas enumeradas (status, type) e booleanas (favorito, permanente) sao
    validadas/normalizadas no load: um valor corrompido (NULL, caixa errada,
    'yes', etc.) levanta DataCorruptionError nomeando o task_id e a coluna,
    em vez de estourar um ValueError opaco de Status()/TaskType().
    """
    task_id = row["id"]
    return Task(
        id=task_id,
        title=row["title"],
        status=Status(_normalize_enum(row["status"], _VALID_STATUS, "status", task_id)),
        type=TaskType(_normalize_enum(row["type"], _VALID_TYPE, "type", task_id)),
        deps=parse_deps(row["deps"] or ""),
        notes=row["notes"] or "",
        order_index=row["order_index"] or 0,
        created_at=row["created_at"] or "",
        completed_at=row["completed_at"],
        hidden_at=row["hidden_at"],
        favorito=_normalize_flag(row["favorito"], "favorito", task_id),
        permanente=_normalize_flag(row["permanente"], "permanente", task_id),
    )


def _row_to_subtask(row: sqlite3.Row) -> Subtask:
    state = int(row["done"] or 0)
    return Subtask(
        id=row["id"],
        task_id=row["task_id"],
        text=row["text"],
        done=state == 2,
        color=row["color"],
        order_index=row["order_index"] or 0,
        state=state,
        notes=row["notes"] or "",
    )


class TaskRepository:
    def __init__(self, conn: sqlite3.Connection, db_path: Path | str = "") -> None:
        self._conn = conn
        self.db_path: str = str(db_path) if db_path else ""
        # Cache lazy (None = ainda nao checado) do suporte a coluna `updated_at`
        # na tabela `subtasks`. A migracao v7 garante `updated_at` em `tasks`
        # (touch incondicional la), mas `subtasks` nao tem a coluna; o touch em
        # update_subtask_text e condicional via _subtasks_has_updated_at().
        self._subtasks_updated_at_supported: bool | None = None

    def create(self, task: Task) -> None:
        self._conn.execute(
            """
            INSERT INTO tasks
                (id, title, status, type, deps, notes, order_index, created_at,
                 favorito, permanente)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.id,
                task.title,
                task.status.value,
                task.type.value,
                ",".join(task.deps),
                task.notes,
                _validate_order_index(task.order_index),
                task.created_at or datetime.now(timezone.utc).isoformat(),
                _flag_to_int(task.favorito, "favorito"),
                _flag_to_int(task.permanente, "permanente"),
            ),
        )
        self._conn.commit()

    def update(self, task_id: str, **fields) -> None:
        """Atualiza colunas arbitrarias de uma task por `id`.

        source.md secao 3.4: este UPDATE generico (usado pelo EditTaskController,
        inclusive para persistir favorito/permanente) e de linha unica e segue o
        mesmo contrato de update_favorito/update_permanente — `rowcount == 0`
        levanta TaskNotFoundError, `rowcount > 1` levanta IntegrityError — e toca
        `updated_at` na mesma transacao.
        """
        allowed = {
            "title",
            "status",
            "type",
            "deps",
            "notes",
            "order_index",
            "completed_at",
            "favorito",
            "permanente",
        }
        col_map: dict[str, object] = {}
        for key, val in fields.items():
            if key not in allowed:
                continue
            if key == "deps" and isinstance(val, list):
                col_map["deps"] = ",".join(val)
            elif key == "status" and isinstance(val, Status):
                col_map["status"] = val.value
            elif key == "type" and isinstance(val, TaskType):
                col_map["type"] = val.value
            elif key in ("favorito", "permanente"):
                col_map[key] = _flag_to_int(val, key)
            elif key == "order_index":
                col_map[key] = _validate_order_index(val)
            else:
                col_map[key] = val

        if not col_map:
            return

        set_parts = [f"{k} = ?" for k in col_map]
        values: list[object] = list(col_map.values())
        # source.md secao 3.4: update() toca updated_at na mesma transacao.
        # A coluna existe a partir da migracao v7 (touch incondicional).
        set_parts.append("updated_at = CURRENT_TIMESTAMP")
        # source.md secao 1.9 / AC-11: ligar `permanente` em uma task que se
        # qualifica para PERMANENT (status == done) des-oculta a task. Como o
        # EditTaskController persiste o toggle de permanente via este UPDATE
        # generico (e nao via update_permanente), a clausula CASE precisa
        # existir tambem aqui. A clausula so e emitida quando permanente=True
        # esta sendo escrito; favorito nunca afeta hidden_at. O status usado e
        # o efetivo apos este UPDATE (col_map["status"] quando o caller tambem
        # muda o status na mesma chamada, senao a coluna status corrente).
        if col_map.get("permanente") == 1:
            if "status" in col_map:
                set_parts.append(
                    "hidden_at = CASE WHEN ? = 'done' THEN NULL ELSE hidden_at END"
                )
                values.append(col_map["status"])
            else:
                set_parts.append(
                    "hidden_at = CASE WHEN status = 'done' THEN NULL ELSE hidden_at END"
                )

        set_clause = ", ".join(set_parts)
        cursor = self._conn.execute(
            f"UPDATE tasks SET {set_clause} WHERE id = ?", values + [task_id]
        )
        self._conn.commit()
        # source.md invariante 8: UPDATE de linha unica que nao afeta nenhuma
        # linha (task sumiu numa corrida) e falha, nao no-op silencioso — senao
        # o caller trata como sucesso e a UI diverge do DB.
        _enforce_single_row(cursor.rowcount, task_id, "update")

    def delete(self, task_id: str) -> None:
        self._conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self._conn.commit()

    def update_notes(self, task_id: str, notes: str) -> None:
        cursor = self._conn.execute(
            "UPDATE tasks SET notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (notes, task_id),
        )
        self._conn.commit()
        _enforce_single_row(cursor.rowcount, task_id, "update_notes")

    def _update_flag(
        self, task_id: str, column: str, value: bool, *, unhide_if_done: bool = False
    ) -> None:
        """Atualiza uma coluna booleana (favorito|permanente) de uma task.

        Valida o range booleano na entrada (ValueError se nao for True/False),
        levanta TaskNotFoundError quando nenhuma linha foi afetada e
        sqlite3.IntegrityError quando mais de uma linha foi afetada (id deveria
        ser unico). Toca `updated_at` incondicionalmente na mesma query — a
        coluna existe a partir da migracao v7 (source.md secao 3.4).

        `unhide_if_done` (source.md secao 1.9 / AC-11): quando True E o flag
        esta sendo ligado (value=True), a mesma query zera `hidden_at` se a
        task se qualifica para PERMANENT (status == 'done'). Caso o status nao
        seja 'done', ou value=False, `hidden_at` e preservado pelo CASE. So
        update_permanente passa unhide_if_done=True; favorito nunca afeta
        hidden_at.
        """
        flag = _flag_to_int(value, column)
        set_clause = f"{column} = ?, updated_at = CURRENT_TIMESTAMP"
        if unhide_if_done and flag == 1:
            set_clause += (
                ", hidden_at = CASE WHEN status = 'done' THEN NULL ELSE hidden_at END"
            )
        cursor = self._conn.execute(
            f"UPDATE tasks SET {set_clause} WHERE id = ?",
            (flag, task_id),
        )
        self._conn.commit()
        _enforce_single_row(cursor.rowcount, task_id, f"update de '{column}'")

    def update_favorito(self, task_id: str, value: bool) -> None:
        """Marca/desmarca uma task como favorita. Ver _update_flag para contratos.

        Favorito nunca afeta `hidden_at` (source.md secao 1.9).
        """
        self._update_flag(task_id, "favorito", value)

    def update_permanente(self, task_id: str, value: bool) -> None:
        """Marca/desmarca uma task como permanente. Ver _update_flag para contratos.

        Ligar `permanente` em uma task oculta com status == 'done' tambem zera
        `hidden_at` (source.md secao 1.9 / AC-11) via unhide_if_done.
        """
        self._update_flag(task_id, "permanente", value, unhide_if_done=True)

    def list_active(self) -> list[Task]:
        rows = self._conn.execute(
            "SELECT * FROM tasks WHERE hidden_at IS NULL ORDER BY order_index ASC, created_at ASC"
        ).fetchall()
        return [_row_to_task(r) for r in rows]

    def list_trash(self) -> list[Task]:
        # Sqlite3 nao suporta NULLS LAST nativo; usar IS NULL como primeiro criterio de ordem
        rows = self._conn.execute(
            "SELECT * FROM tasks WHERE hidden_at IS NOT NULL"
            " ORDER BY completed_at IS NULL, completed_at DESC"
        ).fetchall()
        return [_row_to_task(r) for r in rows]

    def get_by_id(self, task_id: str) -> Task | None:
        row = self._conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return _row_to_task(row) if row else None

    def mark_hidden(self, task_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute("UPDATE tasks SET hidden_at = ? WHERE id = ?", (now, task_id))
        self._conn.commit()

    def _filter_existing_deps(self, deps: list[str]) -> list[str]:
        """Retorna apenas os dep IDs que ainda existem na tabela tasks."""
        if not deps:
            return []
        placeholders = ",".join("?" * len(deps))
        rows = self._conn.execute(
            f"SELECT id FROM tasks WHERE id IN ({placeholders})", deps
        ).fetchall()
        existing = {r["id"] for r in rows}
        return [d for d in deps if d in existing]

    def restore(self, task_id: str) -> None:
        row = self._conn.execute(
            "SELECT deps FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        current_deps = []
        if row:
            current_deps = [d for d in (row["deps"] or "").split(",") if d]
        clean_deps = self._filter_existing_deps(current_deps)
        self._conn.execute(
            "UPDATE tasks SET hidden_at = NULL, deps = ? WHERE id = ?",
            (",".join(clean_deps), task_id),
        )
        self._conn.commit()

    def exists(self, task_id: str) -> bool:
        row = self._conn.execute("SELECT 1 FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return row is not None

    def update_status(
        self,
        task_id: str,
        status: Status,
        completed_at: datetime | None,
    ) -> None:
        """Atualiza status + completed_at de uma task por `id`.

        source.md invariante 8 / secao 3.4: UPDATE de linha unica — `rowcount`
        e validado (`0` -> TaskNotFoundError, `>1` -> IntegrityError) para que
        uma escrita perdida numa corrida nao seja tratada como sucesso. Toca
        `updated_at` na mesma transacao.
        """
        completed_str = completed_at.isoformat() if completed_at is not None else None
        cursor = self._conn.execute(
            "UPDATE tasks SET status = ?, completed_at = ?, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status.value, completed_str, task_id),
        )
        self._conn.commit()
        _enforce_single_row(cursor.rowcount, task_id, "update_status")

    def update_order_indexes(self, pairs: list[tuple[str, int]]) -> None:
        """Aplica novos `order_index` em lote e renormaliza para 0..N-1.

        Cada `order_index` recebido e validado (>= 0, inteiro). Apos aplicar os
        pares informados, os indices de TODAS as tasks ativas (hidden_at IS NULL)
        sao renormalizados para uma sequencia contigua 0..N-1 respeitando a
        ordenacao canonica `(favorito DESC, order_index ASC, id ASC)`, eliminando
        buracos e colisoes silenciosas. O contrato de ordem nao muda — apenas os
        valores ficam densos e deterministicos.
        """
        if not pairs:
            return
        validated = [
            (_validate_order_index(order_index), task_id)
            for task_id, order_index in pairs
        ]
        with self._conn:
            self._conn.executemany(
                "UPDATE tasks SET order_index = ?, updated_at = CURRENT_TIMESTAMP "
                "WHERE id = ?",
                validated,
            )
            # Renormalizacao: reescreve order_index 0..N-1 na ordem canonica.
            # favorito DESC mantem favoritos no topo; order_index ASC, id ASC
            # desempata de forma estavel (source.md invariante 9).
            ordered_ids = [
                r["id"]
                for r in self._conn.execute(
                    "SELECT id FROM tasks WHERE hidden_at IS NULL "
                    "ORDER BY favorito DESC, order_index ASC, id ASC"
                )
            ]
            self._conn.executemany(
                "UPDATE tasks SET order_index = ? WHERE id = ?",
                [(idx, task_id) for idx, task_id in enumerate(ordered_ids)],
            )

    def hide_all_done(self) -> HideAllDoneResult:
        """Vassoura: oculta tasks DONE nao-permanentes; preserva as permanentes.

        Retorna um HideAllDoneResult com `affected_count` (tasks ocultadas) e
        `excluded_permanente_count` (tasks DONE permanentes ainda visiveis que
        a vassoura deliberadamente NAO ocultou). O resultado e comparavel a int
        via `affected_count` para compatibilidade com callers legados; ver a
        docstring de HideAllDoneResult. source.md secoes 1.7 / 2.4 / 9.
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._conn:
            # Conta primeiro as permanentes DONE ainda visiveis que serao
            # deliberadamente puladas — a observabilidade da secao 9 exige
            # excluded_permanente_count, nao so a contagem afetada.
            excluded = self._conn.execute(
                "SELECT COUNT(*) FROM tasks "
                "WHERE status = ? AND permanente = 1 AND hidden_at IS NULL",
                (Status.DONE.value,),
            ).fetchone()[0]
            cursor = self._conn.execute(
                "UPDATE tasks SET hidden_at = ? "
                "WHERE status = ? AND permanente = 0 AND hidden_at IS NULL",
                (now, Status.DONE.value),
            )
            return HideAllDoneResult(
                affected_count=cursor.rowcount,
                excluded_permanente_count=int(excluded),
            )

    def list_subtasks(self, task_id: str) -> list[Subtask]:
        rows = self._conn.execute(
            "SELECT * FROM subtasks WHERE task_id = ? ORDER BY order_index ASC, created_at ASC",
            (task_id,),
        ).fetchall()
        return [_row_to_subtask(row) for row in rows]

    def create_subtask(self, subtask: Subtask) -> None:
        self._conn.execute(
            """
            INSERT INTO subtasks (id, task_id, text, done, color, order_index, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                subtask.id,
                subtask.task_id,
                subtask.text,
                subtask.state if subtask.state else (2 if subtask.done else 0),
                subtask.color,
                _validate_order_index(subtask.order_index),
                subtask.notes,
            ),
        )
        self._conn.commit()

    def update_subtask_done(self, subtask_id: str, done: bool) -> None:
        self.update_subtask_state(subtask_id, 2 if done else 0)

    def update_subtask_state(self, subtask_id: str, state: int) -> None:
        self._conn.execute(
            "UPDATE subtasks SET done = ? WHERE id = ?",
            (state, subtask_id),
        )
        self._conn.commit()

    def update_subtask_order_indexes(self, pairs: list[tuple[str, int]]) -> None:
        if not pairs:
            return
        validated = [
            (_validate_order_index(order_index), subtask_id)
            for subtask_id, order_index in pairs
        ]
        with self._conn:
            self._conn.executemany(
                "UPDATE subtasks SET order_index = ? WHERE id = ?",
                validated,
            )

    def delete_done_subtasks(self, task_id: str) -> int:
        with self._conn:
            cursor = self._conn.execute(
                "DELETE FROM subtasks WHERE task_id = ? AND done = 2",
                (task_id,),
            )
            return cursor.rowcount

    def update_subtask_notes(self, subtask_id: str, notes: str) -> None:
        self._conn.execute(
            "UPDATE subtasks SET notes = ? WHERE id = ?",
            (notes, subtask_id),
        )
        self._conn.commit()

    def _subtasks_has_updated_at(self) -> bool:
        """Detecta (uma vez por instancia) se a tabela `subtasks` tem updated_at.

        A migracao v7 adiciona `updated_at` a `tasks`, mas nao a `subtasks`. O
        touch em update_subtask_text e condicional para nao quebrar com
        `no such column` enquanto a coluna nao existir em `subtasks`.
        """
        if self._subtasks_updated_at_supported is None:
            cols = {
                row[1] for row in self._conn.execute("PRAGMA table_info(subtasks)")
            }
            self._subtasks_updated_at_supported = "updated_at" in cols
        return self._subtasks_updated_at_supported

    def update_subtask_text(self, subtask_id: str, text: str) -> None:
        """Persiste o texto de uma subtask (edicao inline da subtask pane).

        Substitui a escrita RAW `repo._conn.execute()` que a UI fazia sem
        boundary, sem checagem de rowcount e sem tratamento de erro. Valida a
        entrada, roda o UPDATE no mesmo estilo de conexao/transacao dos demais
        metodos e aplica o contrato de linha unica:

        - `text` deve ser str -> ValueError caso contrario;
        - `rowcount == 0` -> SubtaskNotFoundError (a subtask sumiu);
        - `rowcount > 1`  -> sqlite3.IntegrityError (id duplicado);
        - toca `updated_at` se a tabela `subtasks` tiver a coluna (condicional;
          ver _subtasks_has_updated_at).
        """
        if not isinstance(text, str):
            raise ValueError(
                f"text deve ser str; recebido {text!r} do tipo "
                f"{type(text).__name__}"
            )
        set_clause = "text = ?"
        if self._subtasks_has_updated_at():
            set_clause += ", updated_at = CURRENT_TIMESTAMP"
        cursor = self._conn.execute(
            f"UPDATE subtasks SET {set_clause} WHERE id = ?",
            (text, subtask_id),
        )
        self._conn.commit()
        if cursor.rowcount == 0:
            raise SubtaskNotFoundError(f"Subtask {subtask_id!r} não encontrada")
        if cursor.rowcount > 1:
            raise sqlite3.IntegrityError(
                f"update_subtask_text afetou {cursor.rowcount} linhas para "
                f"id {subtask_id!r}; a coluna id deveria ser unica"
            )
