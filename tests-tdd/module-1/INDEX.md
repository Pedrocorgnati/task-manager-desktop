# TDD Suite — module-1-gestao-de-tasks

Locked: pending (run `/tdd:lock` after review)

RED baseline: 65 testes (7 removidos apos remocao do campo `projeto`) / 0 green_leaked / 0 environmental

Generated at: 2026-05-17T06:11:54Z


| TID | Suite | Arquivo::funcao | Covers | Status |
|-----|-------|-----------------|--------|--------|
| TID-1-1-001 | acceptance | `tests-tdd/module-1/acceptance/test_us001_create.py::test_create_no_deps_defaults` | TASK-1/ST005 — US-001#1 | RED |
| TID-1-1-002 | acceptance | `tests-tdd/module-1/acceptance/test_us001_create.py::test_create_with_valid_open_deps` | TASK-1/ST005 — US-001#2 | RED |
| TID-1-1-003 | acceptance | `tests-tdd/module-1/acceptance/test_us001_create.py::test_empty_title_blocks_submit` | TASK-1/ST001 — US-001#3 | RED |
| TID-1-1-004 | acceptance | `tests-tdd/module-1/acceptance/test_us001_create.py::test_invalid_dep_id_silently_dropped` | TASK-1/ST005 — US-001#4 | RED |
| TID-1-1-005 | acceptance | `tests-tdd/module-1/acceptance/test_us001_create.py::test_cycle_resolved_with_toast` | TASK-1/ST005 — US-001#5 | RED |
| TID-1-1-006 | acceptance | `tests-tdd/module-1/acceptance/test_us001_create.py::test_create_with_human_type` | TASK-1/ST001 — US-001#6 | RED |
| TID-1-1-009 | acceptance | `tests-tdd/module-1/acceptance/test_us015_empty_state.py::test_task_list_shows_empty_label_when_no_tasks` | TASK-1/ST004 — US-015 | RED |
| TID-1-1-010 | acceptance | `tests-tdd/module-1/acceptance/test_us020_loading_state.py::test_ok_button_disabled_during_create_submit` | TASK-1/ST001 — US-020#1 | RED |
| TID-1-1-011 | acceptance | `tests-tdd/module-1/acceptance/test_us016_io_error.py::test_create_io_error_shows_dialog` | TASK-1/ST005 — US-016#1 | RED |
| TID-1-1-012 | unit | `tests-tdd/module-1/unit/ui/dialogs/test_new_task_dialog.py::test_get_data_parses_deps` | TASK-1/ST001 — TASK-1/ST001 get_data() | RED |
| TID-1-1-013 | unit | `tests-tdd/module-1/unit/ui/dialogs/test_new_task_dialog.py::test_validate_empty_title_marks_field_error_tooltip_and_focus` | TASK-1/ST001 — TASK-1/ST001 validate() | RED |
| TID-1-1-014 | unit | `tests-tdd/module-1/unit/ui/dialogs/test_new_task_dialog.py::test_enter_on_title_triggers_ok_esc_triggers_cancel` | TASK-1/ST001 — TASK-1/ST001 keyboard | RED |
| TID-1-1-015 | unit | `tests-tdd/module-1/unit/ui/test_header_bar.py::test_plus_button_click_emits_new_task_requested_exactly_once` | TASK-1/ST002 — TASK-1/ST002 signal | RED |
| TID-1-1-016 | unit | `tests-tdd/module-1/unit/ui/test_header_bar.py::test_plus_button_exposes_tooltip_and_accessible_name` | TASK-1/ST002 — TASK-1/ST002 a11y | RED |
| TID-1-1-017 | unit | `tests-tdd/module-1/unit/repositories/test_task_repository.py::test_insert_uses_bind_params_and_persists_all_fields` | TASK-1/ST003 — TASK-1/ST003 insert | RED |
| TID-1-1-018 | unit | `tests-tdd/module-1/unit/repositories/test_task_repository.py::test_list_active_returns_only_tasks_without_hidden_at` | TASK-1/ST003 — TASK-1/ST003 list_active | RED |
| TID-1-1-019 | unit | `tests-tdd/module-1/unit/repositories/test_task_repository.py::test_exists_returns_true_when_present_false_otherwise` | TASK-1/ST003 — TASK-1/ST003 exists | RED |
| TID-1-1-020 | unit | `tests-tdd/module-1/unit/ui/test_task_list.py::test_refresh_clears_previous_cards_and_shows_empty_state_when_no_tasks` | TASK-1/ST004 — TASK-1/ST004 refresh | RED |
| TID-1-1-021 | unit | `tests-tdd/module-1/unit/ui/test_task_card_placeholder.py::test_placeholder_renders_id_titulo_status_type` | TASK-1/ST004 — TASK-1/ST004 placeholder | RED |
| TID-1-1-022 | contract | `tests/contracts/test_task_list_contract.py::test_task_list_refresh_signature_is_stable` | TASK-1/ST004 — OVERVIEW.md/Contratos | RED |
| TID-1-1-023 | contract | `tests/contracts/test_header_bar_contract.py::test_header_bar_new_task_requested_is_signal_no_args` | TASK-1/ST002 — OVERVIEW.md/Contratos | RED |
| TID-1-1-024 | integration | `tests/integration/test_create_task_controller.py::test_create_task_controller_happy_path_end_to_end` | TASK-1/ST005 — TASK-1/ST005 happy path | RED |
| TID-1-1-025 | integration | `tests/integration/test_create_task_controller.py::test_create_task_controller_sad_path_io_error_keeps_dialog_open` | TASK-1/ST005 — TASK-1/ST005 sad path | RED |
| TID-1-2-001 | acceptance | `tests-tdd/module-1/acceptance/test_us002_edit.py::test_edit_title_persists_no_sector_change` | TASK-2/ST003 — US-002#1 | RED |
| TID-1-2-002 | acceptance | `tests-tdd/module-1/acceptance/test_us002_edit.py::test_add_open_dep_moves_to_blocked` | TASK-2/ST003 — US-002#2 | RED |
| TID-1-2-003 | acceptance | `tests-tdd/module-1/acceptance/test_us002_edit.py::test_remove_last_dep_moves_to_queue` | TASK-2/ST003 — US-002#3 | RED |
| TID-1-2-004 | acceptance | `tests-tdd/module-1/acceptance/test_us002_edit.py::test_cycle_on_edit_resolved_with_toast` | TASK-2/ST003 — US-002#4 | RED |
| TID-1-2-005 | acceptance | `tests-tdd/module-1/acceptance/test_us002_edit.py::test_change_type_persists_and_updates_card_icon` | TASK-2/ST002+ST003 — US-002#5 | RED |
| TID-1-2-008 | acceptance | `tests-tdd/module-1/acceptance/test_us020_loading_state.py::test_save_button_disabled_during_edit_submit` | TASK-2/ST001 — US-020#2 | RED |
| TID-1-2-009 | acceptance | `tests-tdd/module-1/acceptance/test_us016_io_error.py::test_edit_io_error_shows_dialog` | TASK-2/ST003 — US-016#2 | RED |
| TID-1-2-010 | unit | `tests-tdd/module-1/unit/ui/widgets/test_task_form_widget.py::test_validate_returns_false_and_marks_error_on_empty_title` | TASK-2/ST001 — TASK-2/ST001 form | RED |
| TID-1-2-011 | unit | `tests-tdd/module-1/unit/ui/dialogs/test_edit_task_dialog.py::test_edit_dialog_prefills_all_four_fields_from_task` | TASK-2/ST001 — TASK-2/ST001 prefill | RED |
| TID-1-2-012 | unit | `tests-tdd/module-1/unit/ui/test_task_card.py::test_task_card_renders_three_rows_meta_title_status` | TASK-2/ST002 — TASK-2/ST002 render | RED |
| TID-1-2-013 | unit | `tests-tdd/module-1/unit/ui/test_task_card.py::test_menu_button_has_exactly_edit_and_delete_actions` | TASK-2/ST002 — TASK-2/ST002 menu | RED |
| TID-1-2-014 | unit | `tests-tdd/module-1/unit/ui/test_task_card.py::test_selected_signal_emitted_on_click_outside_segmented_and_menu` | TASK-2/ST002 — TASK-2/ST002 selected | RED |
| TID-1-2-015 | unit | `tests-tdd/module-1/unit/ui/test_task_card.py::test_card_applies_correct_border_color_per_sector` | TASK-2/ST002 — TASK-2/ST002 border | RED |
| TID-1-2-016 | unit | `tests-tdd/module-1/unit/ui/test_task_card.py::test_title_label_uses_plain_text_format` | TASK-2/ST002 — TASK-2/ST002 anti-XSS | RED |
| TID-1-2-017 | unit | `tests-tdd/module-1/unit/ui/widgets/test_status_segmented_control.py::test_segmented_control_selects_correct_button_by_status_and_open_deps` | TASK-2/ST002 — TASK-2/ST002 segmented | RED |
| TID-1-2-018 | unit | `tests-tdd/module-1/unit/ui/widgets/test_status_segmented_control.py::test_status_changed_emits_canonical_str_values` | TASK-2/ST002 — TASK-2/ST002 signal | RED |
| TID-1-2-019 | unit | `tests-tdd/module-1/unit/repositories/test_task_repository.py::test_update_applies_three_fields_via_bind_where_id` | TASK-2/ST003 — TASK-2/ST003 update | RED |
| TID-1-2-020 | contract | `tests/contracts/test_task_card_contract.py::test_task_card_constructor_accepts_task_callbacks_all_tasks` | TASK-2/ST002 — OVERVIEW.md/Contratos | RED |
| TID-1-2-021 | contract | `tests/contracts/test_status_segmented_control_contract.py::test_status_segmented_control_status_changed_signal_str_canonical_values` | TASK-2/ST002 — OVERVIEW.md/Contratos | RED |
| TID-1-2-023 | integration | `tests/integration/test_edit_task_controller.py::test_edit_task_controller_happy_path_end_to_end` | TASK-2/ST003 — TASK-2/ST003 happy | RED |
| TID-1-2-024 | integration | `tests/integration/test_edit_task_controller.py::test_edit_task_controller_recompute_only_one_level_deep` | TASK-2/ST003 — TASK-2/ST003 RF-008 | RED |
| TID-1-3-001 | acceptance | `tests-tdd/module-1/acceptance/test_us003_delete.py::test_delete_removes_immediately_without_confirmation` | TASK-3/ST002 — US-003#1 | RED |
| TID-1-3-002 | acceptance | `tests-tdd/module-1/acceptance/test_us003_delete.py::test_dependents_recompute_sector_one_level` | TASK-3/ST002 — US-003#2 | RED |
| TID-1-3-003 | acceptance | `tests-tdd/module-1/acceptance/test_us003_delete.py::test_delete_io_error_preserves_state` | TASK-3/ST002 — US-003#3 / US-016#3 | RED |
| TID-1-3-004 | acceptance | `tests-tdd/module-1/acceptance/test_us019_viewer_reset.py::test_viewer_resets_when_selected_task_deleted` | TASK-3/ST002 — US-019#1 | RED |
| TID-1-3-005 | acceptance | `tests-tdd/module-1/acceptance/test_us019_viewer_reset.py::test_viewer_unaffected_when_other_task_deleted` | TASK-3/ST002 — US-019#2 | RED |
| TID-1-3-006 | acceptance | `tests-tdd/module-1/acceptance/test_us019_viewer_reset.py::test_io_error_does_not_reset_viewer` | TASK-3/ST002 — US-019#3 | RED |
| TID-1-3-007 | acceptance | `tests-tdd/module-1/acceptance/test_us017_migration_docs.py::test_readme_documents_one_by_one_flow` | TASK-3/ST003 — US-017#1 | RED |
| TID-1-3-008 | acceptance | `tests-tdd/module-1/acceptance/test_us017_migration_docs.py::test_readme_documents_subtasks_via_deps_pattern` | TASK-3/ST003 — US-017#2 | RED |
| TID-1-3-009 | acceptance | `tests-tdd/module-1/acceptance/test_us017_migration_docs.py::test_readme_mentions_nfr_limit_and_backup` | TASK-3/ST003 — US-017#3 | RED |
| TID-1-3-010 | unit | `tests-tdd/module-1/unit/repositories/test_task_repository.py::test_delete_is_hard_delete_and_noop_on_missing_id` | TASK-3/ST001 — TASK-3/ST001 delete | RED |
| TID-1-3-011 | unit | `tests-tdd/module-1/unit/repositories/test_task_repository.py::test_list_trash_returns_only_tasks_with_hidden_at_not_null` | TASK-3/ST001 — TASK-3/ST001 list_trash | RED |
| TID-1-3-012 | unit | `tests-tdd/module-1/unit/repositories/test_task_repository.py::test_get_by_id_returns_task_or_none` | TASK-3/ST001 — TASK-3/ST001 get_by_id | RED |
| TID-1-3-013 | unit | `tests-tdd/module-1/unit/repositories/test_task_repository.py::test_mark_hidden_in_single_transaction_rollback_on_failure` | TASK-3/ST001 — TASK-3/ST001 mark_hidden | RED |
| TID-1-3-014 | unit | `tests-tdd/module-1/unit/repositories/test_task_repository.py::test_restore_sets_hidden_at_to_null` | TASK-3/ST001 — TASK-3/ST001 restore | RED |
| TID-1-3-016 | unit | `tests-tdd/module-1/unit/repositories/test_task_repository.py::test_init_exposes_db_path_as_public_attribute` | TASK-3/ST001 — TASK-3/ST001 init | RED |
| TID-1-3-017 | contract | `tests/contracts/test_task_repository_contract.py::test_task_repository_facade_exposes_eight_public_methods` | TASK-3/ST001 — OVERVIEW.md/Contratos facade | RED |
| TID-1-3-018 | integration | `tests/integration/test_delete_task_controller.py::test_delete_task_controller_handle_end_to_end` | TASK-3/ST002 — TASK-3/ST002 wire-up | RED |
| TID-1-3-019 | integration | `tests/integration/test_delete_task_controller.py::test_delete_task_controller_recompute_only_one_level_deep` | TASK-3/ST002 — TASK-3/ST002 RF-008 | RED |
| TID-1-3-020 | integration | `tests/integration/test_delete_task_controller.py::test_delete_task_controller_io_error_preserves_state` | TASK-3/ST002 — TASK-3/ST002 sad path | RED |
| TID-1-3-021 | integration | `tests/integration/test_delete_task_controller.py::test_delete_task_controller_never_calls_qmessagebox_confirmation` | TASK-3/ST002 — RF-005 anti-confirm | RED |
| TID-1-3-022 | integration | `tests/integration/test_delete_task_controller.py::test_delete_task_controller_smoke_crud_three_tasks` | TASK-3/ST002 — TASK-3/ST002 smoke | RED |

## Resumo por kind

| Kind | Count |
|------|-------|
| acceptance | 25 |
| unit | 26 |
| contract | 5 |
| integration | 9 |
| **total** | **65** |

## Proximos passos

1. Revisar adversarial summary impresso por `/tdd:create-suite`.
2. Rodar `/tdd:lock {module_path}` para congelar a suite e transitar `creation -> execution`.
3. Em B.3: `/execute-task --module 1 --task K` aplica RED -> GREEN por subtask.
