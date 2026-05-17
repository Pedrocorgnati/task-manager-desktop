# TDD Suite - module-0-foundations

Locked: pending (run `/tdd:lock` after review)
Module type: foundations
Required suites: unit, contract, integration, acceptance
RED baseline: 79 testes / 79 red / 0 green_leaked / 0 environmental (gerado 2026-05-17)

| TID | Suite | Arquivo | Covers | Classificacao | Status |
|-----|-------|---------|--------|---------------|--------|
| TID-0-1-001 | unit | `unit/core/test_db.py` | TASK-1/ST002 BDD#1 | SUCCESS | RED |
| TID-0-1-002 | unit | `unit/core/test_db.py` | TASK-1/ST002 BDD#1 | SUCCESS | RED |
| TID-0-1-003 | unit | `unit/core/test_db.py` | TASK-1/ST002 BDD#1 | SUCCESS | RED |
| TID-0-1-004 | unit | `unit/core/test_db.py` | TASK-1/ST002 BDD#2 | EDGE | RED |
| TID-0-1-005 | unit | `unit/core/test_db.py` | TASK-1/ST002 BDD#3 | ERROR | RED |
| TID-0-1-006 | unit | `unit/core/test_db.py` | TASK-1/ST002 BDD#4 | ERROR | RED |
| TID-0-1-007 | unit | `unit/core/test_db.py` | TASK-1/ST002 BDD#5 | SUCCESS | RED |
| TID-0-1-008 | integration | `integration/test_bootstrap.py` | TASK-1/ST003 BDD#1, US-014 | SUCCESS | RED |
| TID-0-1-009 | integration | `integration/test_bootstrap.py` | TASK-1/ST003 BDD#2, US-014 cen.2 | EDGE | RED |
| TID-0-1-010 | integration | `integration/test_bootstrap.py` | TASK-1/ST003 BDD#3, US-013 cen.3 | ERROR | RED |
| TID-0-1-011 | integration | `integration/test_bootstrap.py` | TASK-1/ST003 BDD#4 | SUCCESS | RED |
| TID-0-1-012 | acceptance | `acceptance/test_app_bootstrap.py` | TASK-1/ST004 BDD#1, US-013 | SUCCESS | RED |
| TID-0-1-013 | acceptance | `acceptance/test_app_bootstrap.py` | TASK-1/ST004 BDD#2 | SUCCESS | RED |
| TID-0-1-014 | acceptance | `acceptance/test_app_bootstrap.py` | TASK-1/ST004 BDD#3 | SUCCESS | RED |
| TID-0-1-015 | acceptance | `acceptance/test_app_bootstrap.py` | TASK-1/ST004 BDD#4, US-013 cen.3, US-016 cen.2 | ERROR | RED |
| TID-0-1-016 | acceptance | `acceptance/test_app_bootstrap.py` | TASK-1/ST004 BDD#5, US-016 cen.3 | DEGRADED | RED |
| TID-0-1-017 | contract | `contract/test_core_db_contract.py` | OVERVIEW Contratos | SUCCESS | RED |
| TID-0-1-018 | contract | `contract/test_core_bootstrap_contract.py` | OVERVIEW Contratos | SUCCESS | RED |
| TID-0-2-001 | unit | `unit/core/test_models.py` | TASK-2/ST001 BDD#1 | SUCCESS | RED |
| TID-0-2-002 | unit | `unit/core/test_models.py` | TASK-2/ST001 BDD#2 | EDGE | RED |
| TID-0-2-003 | unit | `unit/core/test_models.py` | TASK-2/ST001 BDD#3 | SUCCESS | RED |
| TID-0-2-004 | unit | `unit/core/test_models.py` | TASK-2/ST001 BDD#4 | SUCCESS | RED |
| TID-0-2-005 | unit | `unit/core/test_models.py` | OVERVIEW Contratos + ARCHITECTURE | SUCCESS | RED |
| TID-0-2-006 | unit | `unit/core/test_models.py` | OVERVIEW Contratos | SUCCESS | RED |
| TID-0-2-007 | unit | `unit/core/test_models.py` | TASK-2/ST001 BDD#5 | EDGE | RED |
| TID-0-2-008 | unit | `unit/core/test_models.py` | TASK-2/ST001 BDD#6 | EDGE | RED |
| TID-0-2-009 | unit | `unit/core/test_models.py` | TASK-2/ST001 BDD#7 | SUCCESS | RED |
| TID-0-2-010 | unit | `unit/core/test_sector.py` | OVERVIEW Contratos compute_sector, US-005 | SUCCESS | RED |
| TID-0-2-011 | unit | `unit/core/test_sector.py` | TASK-2/ST002 BDD#1, US-001 cen.4 | EDGE | RED |
| TID-0-2-012 | unit | `unit/core/test_id_gen.py` | TASK-2/ST003 BDD#1 | SUCCESS | RED |
| TID-0-2-013 | unit | `unit/core/test_id_gen.py` | TASK-2/ST003 BDD#2 | EDGE | RED |
| TID-0-2-014 | unit | `unit/core/test_id_gen.py` | TASK-2/ST003 regra canonica | SUCCESS | RED |
| TID-0-2-015 | unit | `unit/core/test_cycles.py` | TASK-2/ST004 BDD#1, ARCHITECTURE D-006 | SUCCESS | RED |
| TID-0-2-016 | unit | `unit/core/test_cycles.py` | TASK-2/ST004 BDD#2 | SUCCESS | RED |
| TID-0-2-017 | unit | `unit/core/test_cycles.py` | TASK-2/ST004 BDD#3, US-001 cen.4 | EDGE | RED |
| TID-0-2-018 | unit | `unit/core/test_cycles.py` | TASK-2/ST004 regra D-006 | SUCCESS | RED |
| TID-0-2-019 | integration | `integration/test_cleanup.py` | TASK-2/ST005 BDD#1, US-011 | SUCCESS | RED |
| TID-0-2-020 | integration | `integration/test_cleanup.py` | TASK-2/ST005 BDD#2, US-011 | SUCCESS | RED |
| TID-0-2-021 | integration | `integration/test_cleanup.py` | TASK-2/ST005 BDD#3 | EDGE | RED |
| TID-0-2-022 | integration | `integration/test_cleanup.py` | TASK-2/ST005 BDD#4, US-016 cen.3 | DEGRADED | RED |
| TID-0-2-023 | integration | `integration/test_cleanup.py` | TASK-2/ST005 nota tecnica | EDGE | RED |
| TID-0-2-024 | contract | `contract/test_core_init_contract.py` | OVERVIEW Contratos | SUCCESS | RED |
| TID-0-2-025 | contract | `contract/test_core_sector_contract.py` | OVERVIEW Contratos | SUCCESS | RED |
| TID-0-2-026 | contract | `contract/test_core_cycles_contract.py` | OVERVIEW Contratos | SUCCESS | RED |
| TID-0-2-027 | contract | `contract/test_core_layering_gate.py` | OVERVIEW DoD, AC-T-004, ARCHITECTURE D-001 | SUCCESS | RED |
| TID-0-3-001 | acceptance | `acceptance/test_toast_widget.py` | TASK-3/ST001 BDD#1, US-001 cen.5 | SUCCESS | RED |
| TID-0-3-002 | acceptance | `acceptance/test_toast_widget.py` | TASK-3/ST001 BDD#2 | EDGE | RED |
| TID-0-3-003 | acceptance | `acceptance/test_toast_widget.py` | TASK-3/ST001 AC-001 | SUCCESS | RED |
| TID-0-3-004 | acceptance | `acceptance/test_toast_widget.py` | TASK-3/ST001 implementacao | EDGE | RED |
| TID-0-3-005 | acceptance | `acceptance/test_error_dialog.py` | TASK-3/ST002 BDD#1, US-016 | SUCCESS | RED |
| TID-0-3-006 | acceptance | `acceptance/test_error_dialog.py` | TASK-3/ST002 BDD#2 | SUCCESS | RED |
| TID-0-3-007 | acceptance | `acceptance/test_error_dialog.py` | TASK-3/ST002 BDD#3 | SUCCESS | RED |
| TID-0-3-008 | acceptance | `acceptance/test_error_dialog.py` | TASK-3/ST002 gate secrets-scan | ERROR | RED |
| TID-0-3-009 | acceptance | `acceptance/test_error_dialog.py` | US-016 cen.1, OVERVIEW Risco | SUCCESS | RED |
| TID-0-3-010 | acceptance | `acceptance/test_empty_state.py` | TASK-3/ST003 BDD#1 | SUCCESS | RED |
| TID-0-3-011 | acceptance | `acceptance/test_empty_state.py` | TASK-3/ST003 BDD#2, US-015 | EDGE | RED |
| TID-0-3-012 | acceptance | `acceptance/test_main_window.py` | TASK-3/ST004 BDD#1 | SUCCESS | RED |
| TID-0-3-013 | acceptance | `acceptance/test_main_window.py` | OVERVIEW FAQ MainWindowShell setStyleSheet | SUCCESS | RED |
| TID-0-3-014 | acceptance | `acceptance/test_main_window.py` | OVERVIEW Risco memory leak | SUCCESS | RED |
| TID-0-3-015 | acceptance | `acceptance/test_main_window.py` | OVERVIEW Contratos | SUCCESS | RED |
| TID-0-3-016 | acceptance | `acceptance/test_main_window.py` | OVERVIEW Contratos | SUCCESS | RED |
| TID-0-3-017 | acceptance | `acceptance/test_main_window.py` | TASK-3/ST004 BDD#3, TASK-1 AC-007 | SUCCESS | RED |
| TID-0-3-018 | acceptance | `acceptance/test_main_window.py` | TASK-3/ST004 BDD#4, US-010 | SUCCESS | RED |
| TID-0-3-019 | acceptance | `acceptance/test_main_window.py` | TASK-3/ST004 menubar | SUCCESS | RED |
| TID-0-3-020 | acceptance | `acceptance/test_main_window.py` | TASK-3/ST004 empty states iniciais | SUCCESS | RED |
| TID-0-3-021 | contract | `contract/test_ui_init_contract.py` | OVERVIEW Contratos | SUCCESS | RED |
| TID-0-3-022 | contract | `contract/test_ui_hardcoded_hex_gate.py` | OVERVIEW DoD Qualidade, OVERVIEW Risco hardcode hex | SUCCESS | RED |
| TID-0-3-023 | contract | `contract/test_ui_theme_constants.py` | OVERVIEW Contratos ui.theme | SUCCESS | RED |
| TID-0-4-001 | acceptance | `acceptance/test_docs_and_license.py` | TASK-4/ST001, US-018 | SUCCESS | RED |
| TID-0-4-002 | acceptance | `acceptance/test_docs_and_license.py` | TASK-4/ST001, US-013 | SUCCESS | RED |
| TID-0-4-003 | acceptance | `acceptance/test_docs_and_license.py` | TASK-4/ST001, US-010, RF-011 | SUCCESS | RED |
| TID-0-4-004 | acceptance | `acceptance/test_docs_and_license.py` | TASK-4/ST001, US-018 | SUCCESS | RED |
| TID-0-4-005 | acceptance | `acceptance/test_docs_and_license.py` | OVERVIEW Criterios Qualidade | SUCCESS | RED |
| TID-0-4-006 | acceptance | `acceptance/test_docs_and_license.py` | OVERVIEW Checkpoints | SUCCESS | RED |
| TID-0-4-007 | acceptance | `acceptance/test_docs_and_license.py` | TASK-4/ST002, PRD D-008 | SUCCESS | RED |
| TID-0-4-008 | acceptance | `acceptance/test_docs_and_license.py` | TASK-4/ST003, OVERVIEW Risco dev-deps em runtime | SUCCESS | RED |
| TID-0-4-009 | acceptance | `acceptance/test_docs_and_license.py` | TASK-4/ST003 | SUCCESS | RED |
| TID-0-4-010 | acceptance | `acceptance/test_docs_and_license.py` | OVERVIEW Criterios Qualidade | DEGRADED | RED |
| TID-0-4-011 | acceptance | `acceptance/test_docs_and_license.py` | TASK-4/ST004, OVERVIEW DoD Integracao | SUCCESS | RED |

## Resumo por suite

| Suite | Quantidade |
|-------|-----------:|
| unit | 25 |
| contract | 9 |
| integration | 9 |
| acceptance | 36 |
| **total** | **79** |

## Arquivos no disco

- `acceptance/test_app_bootstrap.py` (5 TIDs)
- `acceptance/test_docs_and_license.py` (11 TIDs)
- `acceptance/test_empty_state.py` (2 TIDs)
- `acceptance/test_error_dialog.py` (5 TIDs)
- `acceptance/test_main_window.py` (9 TIDs)
- `acceptance/test_toast_widget.py` (4 TIDs)
- `contract/test_core_bootstrap_contract.py` (1 TIDs)
- `contract/test_core_cycles_contract.py` (1 TIDs)
- `contract/test_core_db_contract.py` (1 TIDs)
- `contract/test_core_init_contract.py` (1 TIDs)
- `contract/test_core_layering_gate.py` (1 TIDs)
- `contract/test_core_sector_contract.py` (1 TIDs)
- `contract/test_ui_hardcoded_hex_gate.py` (1 TIDs)
- `contract/test_ui_init_contract.py` (1 TIDs)
- `contract/test_ui_theme_constants.py` (1 TIDs)
- `integration/test_bootstrap.py` (4 TIDs)
- `integration/test_cleanup.py` (5 TIDs)
- `unit/core/test_cycles.py` (4 TIDs)
- `unit/core/test_db.py` (7 TIDs)
- `unit/core/test_id_gen.py` (3 TIDs)
- `unit/core/test_models.py` (9 TIDs)
- `unit/core/test_sector.py` (2 TIDs)
