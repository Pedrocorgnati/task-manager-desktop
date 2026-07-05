from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from task_manager_desktop.core.exceptions import TaskNotFoundError
from task_manager_desktop.core.models import (
    ClockTimer,
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


def _normalize_utc_iso(value: object, field_name: str) -> str:
    """Valida e normaliza timestamps ISO para comparacao lexicografica segura."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} deve ser uma string ISO-8601 nao vazia")
    raw = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{field_name} deve ser ISO-8601 valido") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")


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

    Colunas enumeradas (status) e booleanas (favorito, permanente) sao
    validadas/normalizadas no load: um valor corrompido (NULL, caixa errada,
    'yes', etc.) levanta DataCorruptionError nomeando o task_id e a coluna,
    em vez de estourar um ValueError opaco de Status(). A task nao tem mais
    coluna `type` (migration v10) — o tipo vive nas subtasks.
    """
    task_id = row["id"]
    return Task(
        id=task_id,
        title=row["title"],
        status=Status(_normalize_enum(row["status"], _VALID_STATUS, "status", task_id)),
        deps=parse_deps(row["deps"] or ""),
        notes=row["notes"] or "",
        order_index=row["order_index"] or 0,
        created_at=row["created_at"] or "",
        completed_at=row["completed_at"],
        hidden_at=row["hidden_at"],
        favorito=_normalize_flag(row["favorito"], "favorito", task_id),
        permanente=_normalize_flag(row["permanente"], "permanente", task_id),
        # coin_favorite/dot_favorite chegaram na migration v12; bancos lidos
        # antes dela (ou rows sem a coluna por divergencia) caem em False.
        coin_favorite=(
            _normalize_flag(row["coin_favorite"], "coin_favorite", task_id)
            if "coin_favorite" in row.keys()
            else False
        ),
        dot_favorite=(
            _normalize_flag(row["dot_favorite"], "dot_favorite", task_id)
            if "dot_favorite" in row.keys()
            else False
        ),
        em_preparacao=_normalize_flag(
            row["em_preparacao"], "em_preparacao", task_id
        ),
        # workspace_root chegou na migration v11; bancos lidos antes dela (ou
        # rows sem a coluna por divergencia) caem no default vazio.
        workspace_root=(
            (row["workspace_root"] or "")
            if "workspace_root" in row.keys()
            else ""
        ),
    )


def _row_to_subtask(row: sqlite3.Row) -> Subtask:
    state = int(row["done"] or 0)
    # `type` chegou na migration v9; bancos lidos antes dela (ou rows sem a
    # coluna por divergencia) caem no default canonico 'agent'.
    raw_type = row["type"] if "type" in row.keys() else "agent"
    subtask_type = (
        TaskType(raw_type) if raw_type in _VALID_TYPE else TaskType.AGENT
    )
    return Subtask(
        id=row["id"],
        task_id=row["task_id"],
        text=row["text"],
        done=state == 2,
        color=row["color"],
        order_index=row["order_index"] or 0,
        state=state,
        notes=row["notes"] or "",
        type=subtask_type,
    )


def _row_to_clock_timer(row: sqlite3.Row) -> ClockTimer:
    ends_at = str(row["ends_at"] or "")
    remaining = int(row["remaining_seconds"] or 0)
    if not ends_at:
        ends_at = datetime.now(timezone.utc).isoformat()
    return ClockTimer(
        id=row["id"],
        title=row["title"],
        duration_seconds=int(row["duration_seconds"] or 0),
        remaining_seconds=remaining,
        ends_at=ends_at,
        color=str(row["color"] or "#71717A"),
        state=str(row["state"] or "running"),
        paused=bool(int(row["paused"] or 0)),
        paused_at=row["paused_at"],
        kind=(str(row["kind"]) if ("kind" in row.keys() and row["kind"]) else "normal"),
        created_at=str(row["created_at"] or ""),
        updated_at=str(row["updated_at"] or ""),
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
        self._clock_timer_table_ready = False
        self._permanent_schedule_table_ready = False

    def _ensure_clock_timers_table(self) -> None:
        if self._clock_timer_table_ready:
            return
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clock_timers (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL CHECK(duration_seconds >= 0),
                remaining_seconds INTEGER NOT NULL CHECK(remaining_seconds >= 0),
                ends_at TEXT NOT NULL DEFAULT '',
                color TEXT NOT NULL DEFAULT '#71717A',
                state TEXT NOT NULL CHECK(state IN ('running', 'done')),
                paused INTEGER NOT NULL DEFAULT 0 CHECK(paused IN (0, 1)),
                paused_at TEXT NULL,
                kind TEXT NOT NULL DEFAULT 'normal',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cols = {row[1] for row in self._conn.execute("PRAGMA table_info(clock_timers)")}
        if "paused" not in cols:
            self._conn.execute(
                "ALTER TABLE clock_timers ADD COLUMN paused INTEGER NOT NULL DEFAULT 0 CHECK(paused IN (0, 1))"
            )
        if "ends_at" not in cols:
            self._conn.execute(
                "ALTER TABLE clock_timers ADD COLUMN ends_at TEXT NOT NULL DEFAULT ''"
            )
        if "paused_at" not in cols:
            self._conn.execute(
                "ALTER TABLE clock_timers ADD COLUMN paused_at TEXT NULL"
            )
        if "color" not in cols:
            self._conn.execute(
                "ALTER TABLE clock_timers ADD COLUMN color TEXT NOT NULL DEFAULT '#71717A'"
            )
        if "kind" not in cols:
            # Timers pre-existentes nao tem kind -> migram para a div 'normal'
            # (div Timers), preservando o comportamento atual.
            self._conn.execute(
                "ALTER TABLE clock_timers ADD COLUMN kind TEXT NOT NULL DEFAULT 'normal'"
            )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_clock_timers_state ON clock_timers(state)"
        )
        self._conn.commit()
        self._clock_timer_table_ready = True

    def _ensure_permanent_schedules_table(self) -> None:
        if self._permanent_schedule_table_ready:
            return
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS permanent_task_schedules (
                task_id TEXT PRIMARY KEY REFERENCES tasks(id) ON DELETE CASCADE,
                due_at TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_permanent_task_schedules_due_at "
            "ON permanent_task_schedules(due_at)"
        )
        self._conn.commit()
        self._permanent_schedule_table_ready = True

    def create(self, task: Task) -> None:
        self._conn.execute(
            """
            INSERT INTO tasks
                (id, title, status, deps, notes, order_index, created_at,
                 favorito, permanente, coin_favorite, dot_favorite,
                 em_preparacao, workspace_root)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.id,
                task.title,
                task.status.value,
                ",".join(task.deps),
                task.notes,
                _validate_order_index(task.order_index),
                task.created_at or datetime.now(timezone.utc).isoformat(),
                _flag_to_int(task.favorito, "favorito"),
                _flag_to_int(task.permanente, "permanente"),
                _flag_to_int(task.coin_favorite, "coin_favorite"),
                _flag_to_int(task.dot_favorite, "dot_favorite"),
                _flag_to_int(task.em_preparacao, "em_preparacao"),
                task.workspace_root or "",
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
            "deps",
            "notes",
            "order_index",
            "completed_at",
            "favorito",
            "permanente",
            "coin_favorite",
            "dot_favorite",
            "em_preparacao",
            "workspace_root",
        }
        col_map: dict[str, object] = {}
        for key, val in fields.items():
            if key not in allowed:
                continue
            if key == "deps" and isinstance(val, list):
                col_map["deps"] = ",".join(val)
            elif key == "status" and isinstance(val, Status):
                col_map["status"] = val.value
            elif key in (
                "favorito",
                "permanente",
                "coin_favorite",
                "dot_favorite",
                "em_preparacao",
            ):
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

    def update_em_preparacao(self, task_id: str, value: bool) -> None:
        """Marca/desmarca a flag manual do setor "Em preparação".

        Ver _update_flag para contratos (rowcount, touch de updated_at).
        em_preparacao nunca afeta `hidden_at`.
        """
        self._update_flag(task_id, "em_preparacao", value)

    def update_coin_favorite(self, task_id: str, value: bool) -> None:
        """Marca/desmarca o destaque de moeda. Ver _update_flag para contratos.

        Irmão de `favorito` no ranqueamento; nunca afeta `hidden_at`.
        """
        self._update_flag(task_id, "coin_favorite", value)

    def update_dot_favorite(self, task_id: str, value: bool) -> None:
        """Marca/desmarca o marcador de bolinha. Ver _update_flag para contratos.

        Irmão de `favorito` no ranqueamento; nunca afeta `hidden_at`.
        """
        self._update_flag(task_id, "dot_favorite", value)

    def schedule_permanent_task(self, task_id: str, due_at: str) -> None:
        """Agenda uma task permanente para voltar a IN_PROGRESS em ``due_at``.

        O agendamento e separado do status atual: mover manualmente a task antes
        do vencimento nao cancela nem altera este prazo.
        """
        normalized_due_at = _normalize_utc_iso(due_at, "due_at")
        self._ensure_permanent_schedules_table()
        row = self._conn.execute(
            "SELECT permanente FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise TaskNotFoundError(f"Task {task_id!r} não encontrada")
        if not _normalize_flag(row["permanente"], "permanente", task_id):
            raise ValueError("apenas tasks permanentes podem ser agendadas")
        self._conn.execute(
            """
            INSERT INTO permanent_task_schedules (task_id, due_at)
            VALUES (?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
                due_at = excluded.due_at,
                updated_at = CURRENT_TIMESTAMP
            """,
            (task_id, normalized_due_at),
        )
        self._conn.commit()

    def get_permanent_schedule(self, task_id: str) -> str | None:
        """Retorna o due_at agendado para a task, ou None se não houver."""
        self._ensure_permanent_schedules_table()
        row = self._conn.execute(
            "SELECT due_at FROM permanent_task_schedules WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        return row["due_at"] if row else None

    def trigger_due_permanent_schedules(self, now_iso: str) -> list[Task]:
        """Dispara agendamentos vencidos e retorna as tasks atualizadas.

        Mesmo se a task ja estiver em IN_PROGRESS, o UPDATE e executado para
        tocar updated_at e registrar a ida agendada para execucao.
        """
        normalized_now = _normalize_utc_iso(now_iso, "now_iso")
        self._ensure_permanent_schedules_table()
        with self._conn:
            self._conn.execute(
                """
                DELETE FROM permanent_task_schedules
                WHERE task_id IN (
                    SELECT s.task_id
                    FROM permanent_task_schedules s
                    LEFT JOIN tasks t ON t.id = s.task_id
                    WHERE t.id IS NULL OR t.permanente != 1
                )
                """
            )
            rows = self._conn.execute(
                """
                SELECT s.task_id
                FROM permanent_task_schedules s
                JOIN tasks t ON t.id = s.task_id
                WHERE s.due_at <= ?
                  AND t.permanente = 1
                ORDER BY s.due_at ASC, s.task_id ASC
                """,
                (normalized_now,),
            ).fetchall()
            task_ids = [row["task_id"] for row in rows]
            if not task_ids:
                return []
            self._conn.executemany(
                """
                UPDATE tasks
                SET status = ?, completed_at = NULL, hidden_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                [(Status.IN_PROGRESS.value, task_id) for task_id in task_ids],
            )
            self._conn.executemany(
                "DELETE FROM permanent_task_schedules WHERE task_id = ?",
                [(task_id,) for task_id in task_ids],
            )
        return [
            task
            for task_id in task_ids
            if (task := self.get_by_id(task_id)) is not None
        ]

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

    def subtask_types_by_task(self) -> dict[str, set[str]]:
        """Mapa task_id -> conjunto dos tipos (agent/dev/human) de suas subtasks.

        Consulta unica (sem N+1) usada pelo filtro de tipo do header para decidir
        a visibilidade de cada card principal: um card so e visivel, sob filtro
        ativo, se possuir ao menos uma subtask de um tipo selecionado. Tasks sem
        subtasks simplesmente nao aparecem no mapa (conjunto vazio implicito).
        Valores fora do dominio canonico (banco divergente) caem em 'agent'.
        """
        result: dict[str, set[str]] = {}
        for row in self._conn.execute("SELECT DISTINCT task_id, type FROM subtasks"):
            raw_type = row["type"] if "type" in row.keys() else "agent"
            value = raw_type if raw_type in _VALID_TYPE else "agent"
            result.setdefault(row["task_id"], set()).add(value)
        return result

    def create_subtask(self, subtask: Subtask) -> None:
        self._conn.execute(
            """
            INSERT INTO subtasks (id, task_id, text, done, color, order_index, notes, type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                subtask.id,
                subtask.task_id,
                subtask.text,
                subtask.state if subtask.state else (2 if subtask.done else 0),
                subtask.color,
                _validate_order_index(subtask.order_index),
                subtask.notes,
                subtask.type.value,
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

    def delete_done_subtasks(
        self, task_id: str, types: set[str] | frozenset[str] | None = None
    ) -> int:
        """Remove as subtasks concluidas (done == 2) de uma task.

        Quando `types` e informado, restringe a remocao aos tipos dados — usado
        pela subtask pane quando o filtro de tipo do header esta ativo, para que
        "limpar concluidas" nao apague subtasks de tipos que estao OCULTOS na
        view (perda de dados silenciosa). `types == None` remove todas (o
        comportamento padrao quando o filtro esta inativo / todos os tipos).
        Tipos fora do dominio canonico sao ignorados; lista vazia -> no-op.
        """
        if types is None:
            with self._conn:
                cursor = self._conn.execute(
                    "DELETE FROM subtasks WHERE task_id = ? AND done = 2",
                    (task_id,),
                )
                return cursor.rowcount
        valid = [t for t in types if t in _VALID_TYPE]
        if not valid:
            return 0
        placeholders = ", ".join("?" for _ in valid)
        with self._conn:
            cursor = self._conn.execute(
                f"DELETE FROM subtasks WHERE task_id = ? AND done = 2 "
                f"AND type IN ({placeholders})",
                (task_id, *valid),
            )
            return cursor.rowcount

    def update_subtask_notes(self, subtask_id: str, notes: str) -> None:
        self._conn.execute(
            "UPDATE subtasks SET notes = ? WHERE id = ?",
            (notes, subtask_id),
        )
        self._conn.commit()

    def update_subtask_type(self, subtask_id: str, type: TaskType | str) -> None:
        """Persiste o tipo (agent/dev/human) de uma subtask.

        Aceita tanto TaskType quanto a string canonica; valores fora do dominio
        sao rejeitados antes do UPDATE para nao gravar lixo (o CHECK da coluna
        ja blindaria, mas o fail-fast aqui produz um erro explicito).
        """
        value = type.value if isinstance(type, TaskType) else str(type)
        if value not in _VALID_TYPE:
            raise ValueError(
                f"tipo de subtask invalido {value!r}; esperado um de {_VALID_TYPE}"
            )
        cursor = self._conn.execute(
            "UPDATE subtasks SET type = ? WHERE id = ?",
            (value, subtask_id),
        )
        self._conn.commit()
        if cursor.rowcount == 0:
            # Simetria com update_subtask_text: subtask inexistente e erro
            # explicito, nao um no-op silencioso.
            raise SubtaskNotFoundError(f"Subtask {subtask_id!r} não encontrada")

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

    def list_clock_timers(self, kind: str | None = None) -> list[ClockTimer]:
        """Lista timers. Com ``kind`` informado, restringe à div correspondente
        ('normal' = div Timers, 'daily' = div Daily Timers). Sem ``kind`` (default),
        retorna todos — preserva o contrato histórico de chamadores sem escopo."""
        self._ensure_clock_timers_table()
        if kind is None:
            rows = self._conn.execute(
                "SELECT * FROM clock_timers ORDER BY created_at ASC, id ASC"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM clock_timers WHERE kind = ? ORDER BY created_at ASC, id ASC",
                (kind,),
            ).fetchall()
        return [_row_to_clock_timer(row) for row in rows]

    def create_clock_timer(self, timer: ClockTimer) -> None:
        self._ensure_clock_timers_table()
        self._conn.execute(
            """
            INSERT INTO clock_timers
                (id, title, duration_seconds, remaining_seconds, ends_at, color, state, paused, paused_at, kind)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timer.id,
                timer.title,
                int(timer.duration_seconds),
                int(timer.remaining_seconds),
                timer.ends_at,
                timer.color,
                timer.state,
                1 if timer.paused else 0,
                timer.paused_at,
                timer.kind or "normal",
            ),
        )
        self._conn.commit()

    def update_clock_timer(self, timer: ClockTimer) -> None:
        self._ensure_clock_timers_table()
        cursor = self._conn.execute(
            """
            UPDATE clock_timers
            SET title = ?, duration_seconds = ?, remaining_seconds = ?, ends_at = ?, color = ?,
                state = ?, paused = ?, paused_at = ?, kind = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                timer.title,
                int(timer.duration_seconds),
                int(timer.remaining_seconds),
                timer.ends_at,
                timer.color,
                timer.state,
                1 if timer.paused else 0,
                timer.paused_at,
                timer.kind or "normal",
                timer.id,
            ),
        )
        self._conn.commit()
        if cursor.rowcount == 0:
            raise TaskNotFoundError(f"ClockTimer {timer.id!r} não encontrado")

    def delete_clock_timer(self, timer_id: str) -> None:
        self._ensure_clock_timers_table()
        self._conn.execute("DELETE FROM clock_timers WHERE id = ?", (timer_id,))
        self._conn.commit()
