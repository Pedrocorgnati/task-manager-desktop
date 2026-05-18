# TDD Suite - module-2-setores-dependencias

Locked: pending (run /tdd:lock after review)
RED baseline: 55 testes / 55 red / 0 green_leaked / 0 environmental / 0 signature_drift
Dedupe cross-kind: 13 source_refs sobrepostos analisados; nenhum dupe estrito (cada nivel cobre facet distinto — unit=logica pura, integration=spy de boundary, acceptance=UI com qtbot). Detalhe em §Dedupe.

## Suites por TID

| TID         | Suite       | Arquivo                                                | Test                                                             | Covers                                          | Status |
| ----------- | ----------- | ------------------------------------------------------ | ---------------------------------------------------------------- | ----------------------------------------------- | ------ |
| TID-2-1-001 | acceptance  | `tests/acceptance/test_us_004_status_change.py`        | `test_done_moves_to_completed_sector_with_completed_at`          | US-004#cenario-1                                | RED    |
| TID-2-1-002 | acceptance  | `tests/acceptance/test_us_004_status_change.py`        | `test_in_progress_on_blocked_task_accepted_gray`                 | US-004#cenario-2                                | RED    |
| TID-2-1-003 | acceptance  | `tests/acceptance/test_us_004_status_change.py`        | `test_in_progress_to_pending_recomputes_sector`                  | US-004#cenario-3                                | RED    |
| TID-2-1-004 | acceptance  | `tests/acceptance/test_us_004_status_change.py`        | `test_io_failure_reverts_segmented_control`                      | US-004#cenario-4                                | RED    |
| TID-2-1-005 | unit        | `tests/unit/test_change_status_controller.py`          | `test_pending_to_done_persists_status_and_completed_at`          | TASK-1#ST005, AC-T-001, AC-T-002                | RED    |
| TID-2-1-006 | unit        | `tests/unit/test_change_status_controller.py`          | `test_done_to_pending_clears_completed_at`                       | TASK-1#ST005, AC-T-002                          | RED    |
| TID-2-1-007 | unit        | `tests/unit/test_change_status_controller.py`          | `test_done_to_in_progress_clears_completed_at`                   | TASK-1#ST005, AC-T-002                          | RED    |
| TID-2-1-008 | unit        | `tests/unit/test_change_status_controller.py`          | `test_same_status_is_silent_noop_no_db_write`                    | TASK-1#ST005, AC-T-004                          | RED    |
| TID-2-1-009 | unit        | `tests/unit/test_change_status_controller.py`          | `test_invalid_status_string_is_logged_and_noop`                  | TASK-1#ST005, AC-T-008                          | RED    |
| TID-2-1-010 | unit        | `tests/unit/test_change_status_controller.py`          | `test_repo_operational_error_triggers_show_io_error_and_refresh` | TASK-1#ST005, AC-T-005                          | RED    |
| TID-2-1-011 | unit        | `tests/unit/test_change_status_controller.py`          | `test_pending_with_open_deps_to_in_progress_recomputes_sector`   | TASK-1#ST005, AC-T-003                          | RED    |
| TID-2-1-012 | contract    | `tests/contract/test_task_repository_update_status.py` | `test_update_status_contract_signature_and_persistence`          | TASK-1#ST006, TASK-1#ST001                      | RED    |
| TID-2-1-013 | integration | `tests/integration/test_change_status_flow.py`         | `test_pending_to_done_persists_and_recomputes_sector`            | TASK-1#ST007                                    | RED    |
| TID-2-1-014 | integration | `tests/integration/test_change_status_flow.py`         | `test_done_to_pending_clears_completed_at_in_db`                 | TASK-1#ST007                                    | RED    |
| TID-2-1-015 | integration | `tests/integration/test_change_status_flow.py`         | `test_change_status_p95_under_50ms_100_runs`                     | TASK-1#ST007, AC-T-006                          | RED    |
| TID-2-1-016 | unit        | `tests/unit/test_change_status_controller.py`          | `test_btn_group_disabled_during_write`                           | US-021#cenario-1                                | RED    |
| TID-2-1-017 | unit        | `tests/unit/test_change_status_controller.py`          | `test_btn_group_reenabled_after_io_error`                        | US-021#cenario-2                                | RED    |
| TID-2-1-018 | unit        | `tests/unit/test_change_status_controller.py`          | `test_double_click_does_not_double_write`                        | US-021#cenario-3, AC-T-007                      | RED    |
| TID-2-2-001 | unit        | `tests/unit/test_sector_propagation.py`                | `test_two_dependents_promoted_on_dep_done`                       | TASK-2#ST005, US-005#cenario-1                  | RED    |
| TID-2-2-002 | unit        | `tests/unit/test_sector_propagation.py`                | `test_dependent_with_other_open_dep_stays_blocked`               | TASK-2#ST005, US-005#cenario-2                  | RED    |
| TID-2-2-003 | unit        | `tests/unit/test_sector_propagation.py`                | `test_reverting_done_reblocks_dependents`                        | TASK-2#ST005, US-005#cenario-3                  | RED    |
| TID-2-2-004 | unit        | `tests/unit/test_sector_propagation.py`                | `test_chain_propagation_is_one_level_only`                       | TASK-2#ST005, US-005#cenario-4, AC-T-002, D-006 | RED    |
| TID-2-2-005 | unit        | `tests/unit/test_sector_propagation.py`                | `test_no_dependents_returns_empty`                               | TASK-2#ST005                                    | RED    |
| TID-2-2-006 | unit        | `tests/unit/test_has_open_deps_for.py`                 | `test_invalid_dep_ids_are_ignored`                               | TASK-2#ST005, US-001#cenario-4, AC-T-003        | RED    |
| TID-2-2-007 | unit        | `tests/unit/test_sector_propagation.py`                | `test_self_excluded_from_result`                                 | TASK-2#ST005                                    | RED    |
| TID-2-2-008 | unit        | `tests/unit/test_has_open_deps_for.py`                 | `test_done_dep_does_not_block`                                   | TASK-2#ST005                                    | RED    |
| TID-2-2-009 | unit        | `tests/unit/test_sector_propagation.py`                | `test_function_is_pure_no_mutation`                              | TASK-2#ST005, AC-T-004                          | RED    |
| TID-2-2-010 | integration | `tests/integration/test_propagation_flow.py`           | `test_change_a_to_done_moves_b_c_to_fila`                        | TASK-2#ST006                                    | RED    |
| TID-2-2-011 | integration | `tests/integration/test_propagation_flow.py`           | `test_zero_dependents_does_not_touch_task_list`                  | TASK-2#ST006                                    | RED    |
| TID-2-2-012 | integration | `tests/integration/test_propagation_flow.py`           | `test_threshold_triggers_full_refresh`                           | TASK-2#ST006, AC-T-006                          | RED    |
| TID-2-2-013 | integration | `tests/integration/test_propagation_flow.py`           | `test_error_path_does_not_propagate`                             | TASK-2#ST006, AC-T-008                          | RED    |
| TID-2-2-014 | integration | `tests/integration/test_propagation_flow.py`           | `test_revert_does_not_propagate`                                 | TASK-2#ST006                                    | RED    |
| TID-2-2-015 | acceptance  | `tests/acceptance/test_us_005_propagation.py`          | `test_us_005_cen_1_dependents_promoted_on_done`                  | US-005#cenario-1                                | RED    |
| TID-2-2-016 | acceptance  | `tests/acceptance/test_us_005_propagation.py`          | `test_us_005_cen_2_dependent_with_other_open_dep_stays_blocked`  | US-005#cenario-2                                | RED    |
| TID-2-2-017 | acceptance  | `tests/acceptance/test_us_005_propagation.py`          | `test_us_005_cen_3_revert_status_demotes_dependents`             | US-005#cenario-3                                | RED    |
| TID-2-2-018 | acceptance  | `tests/acceptance/test_us_005_propagation.py`          | `test_us_005_cen_4_chain_propagation_one_level_only`             | US-005#cenario-4, UX-2-2                        | RED    |
| TID-2-2-019 | integration | `tests/benchmark/test_propagation_perf.py`             | `test_propagation_p95_under_50ms_2000_tasks`                     | TASK-2#ST008, AC-T-005                          | RED    |
| TID-2-3-001 | contract    | `tests-tdd/repositories/test_update_order_indexes.py`  | `test_update_order_indexes_persists_in_single_transaction`       | TASK-3#ST001                                    | RED    |
| TID-2-3-002 | contract    | `tests-tdd/repositories/test_update_order_indexes.py`  | `test_update_order_indexes_rollback_on_error`                    | TASK-3#ST001                                    | RED    |
| TID-2-3-003 | contract    | `tests-tdd/repositories/test_update_order_indexes.py`  | `test_update_order_indexes_empty_list_noop`                      | TASK-3#ST001                                    | RED    |
| TID-2-3-004 | acceptance  | `tests-tdd/ui/test_task_list_sectors.py`               | `test_empty_list_renders_4_separators_and_4_placeholders`        | US-022#cenario-1, AC-T-001                      | RED    |
| TID-2-3-005 | acceptance  | `tests-tdd/ui/test_task_list_sectors.py`               | `test_separator_text_never_contains_count`                       | AC-T-001                                        | RED    |
| TID-2-3-006 | acceptance  | `tests-tdd/ui/test_task_list_sectors.py`               | `test_tasks_sorted_by_sector_then_order_index`                   | AC-T-003                                        | RED    |
| TID-2-3-007 | acceptance  | `tests-tdd/ui/test_task_list_sectors.py`               | `test_click_on_separator_does_not_select`                        | AC-T-004                                        | RED    |
| TID-2-3-008 | acceptance  | `tests-tdd/ui/test_task_list_sectors.py`               | `test_click_on_placeholder_does_not_select`                      | US-022#cenario-3, AC-T-002                      | RED    |
| TID-2-3-009 | acceptance  | `tests-tdd/ui/test_task_list_sectors.py`               | `test_click_on_task_emits_task_selected`                         | AC-T-004                                        | RED    |
| TID-2-3-010 | acceptance  | `tests-tdd/ui/test_task_list_sectors.py`               | `test_placeholder_disappears_when_task_added`                    | US-022#cenario-2                                | RED    |
| TID-2-3-011 | acceptance  | `tests-tdd/ui/test_task_list_dnd.py`                   | `test_intra_sector_reorder_succeeds`                             | US-006#cenario-1, AC-T-005                      | RED    |
| TID-2-3-012 | acceptance  | `tests-tdd/ui/test_task_list_dnd.py`                   | `test_cross_sector_drop_is_silent_noop`                          | US-006#cenario-2, AC-T-006                      | RED    |
| TID-2-3-013 | acceptance  | `tests-tdd/ui/test_task_list_dnd.py`                   | `test_drop_on_separator_rejected_silently`                       | AC-T-008                                        | RED    |
| TID-2-3-014 | acceptance  | `tests-tdd/ui/test_task_list_dnd.py`                   | `test_done_sector_blocks_reorder`                                | US-006#cenario-3, AC-T-007                      | RED    |
| TID-2-3-015 | integration | `tests-tdd/ui/test_task_list_dnd.py`                   | `test_reorder_persists_through_restart`                          | US-006#cenario-1, AC-T-009                      | RED    |
| TID-2-3-016 | integration | `tests-tdd/ui/test_task_list_dnd.py`                   | `test_io_failure_reverts_visual_order`                           | US-023#cenario-2, AC-T-010                      | RED    |
| TID-2-3-017 | acceptance  | `tests-tdd/ui/test_task_list_dnd.py`                   | `test_success_drop_shows_info_toast`                             | US-023#cenario-1, AC-T-013                      | RED    |
| TID-2-3-018 | acceptance  | `tests-tdd/ui/test_task_list_dnd.py`                   | `test_rejected_drop_does_not_show_toast`                         | US-023#cenario-3                                | RED    |

## Totais

- Total: 55
- Por kind: unit=19 | contract=4 | integration=11 | acceptance=21
- Por task: TASK-1=18 | TASK-2=19 | TASK-3=18

## Dedupe cross-kind (analise)

Regra: scenarios cobertos por 2+ suites → escolher menor nivel (acceptance < integration < e2e); unit fica se target_file e pura.

Overlaps por source_ref (13 grupos detectados):

| source_ref                     | TIDs sobrepostos                                    | Decisao                                                                                                                             |
| ------------------------------ | --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| US-005#cenario-1..4 (4 grupos) | unit TID-2-2-001..004 + acceptance TID-2-2-015..018 | KEEP ambos — unit testa funcao pura (`compute_sector_change_propagation`), acceptance testa fluxo UI via `qtbot`. Facets distintos. |
| US-006#cenario-1               | acceptance TID-2-3-011 + integration TID-2-3-015    | KEEP ambos — 011 cobre acao UI, 015 cobre invariante de persistencia pos-restart.                                                   |
| AC-T-001..008 (8 grupos)       | varios TIDs unit/integration/acceptance             | KEEP todos — AC-T-\* sao criterios transversais por design (cada nivel cobre facet diferente). Documentado em TEST-PLAN §7.6.       |

Nenhum dupe estrito a remover. Cobertura layered intencional.

## Artefatos relacionados

- `suite-manifest.json` em `output/wbs/task-manager-desktop/modules/module-2-setores-dependencias/`
- `RED-BASELINE.json` em `tests-tdd/module-2/`
- `TEST-PLAN.md` (§7 adversarial self-check) em `output/wbs/.../module-2-setores-dependencias/`

## Tooling fingerprint

- pytest: ver `RED-BASELINE.json.tooling.pytest_version`
- ruff: 0.15.5 (formatter aplicado em 12 arquivos de teste)
- python: 3.10+ (target_version `pyproject.toml`)

## Proximo

`/tdd:lock output/wbs/task-manager-desktop/modules/module-2-setores-dependencias .claude/projects/task-manager-desktop.json` — transita state creation → execution.
