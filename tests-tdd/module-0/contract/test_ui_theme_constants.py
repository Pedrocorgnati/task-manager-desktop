# @tdd-locked: do not edit without /tdd:unlock
# Suite: contract | Module: module-0-foundations | Task: TASK-3
# TIDs: TID-0-3-023
import pytest


class TestUiThemeCanonicalConstants:
    """TID-0-3-023 | covers: OVERVIEW Contratos ui.theme | suite: contract

    Contrato: ui.theme expoe constantes canonicas:
      - WINDOW_DEF_W == 1400
      - WINDOW_DEF_H == 900
      - SPLITTER_SIZES == [560, 840]
      - TOAST_DURATION_MS == 4000
    """

    def test_theme_constants_canonical_values(self):
        from task_manager_desktop.ui import theme

        assert isinstance(theme.WINDOW_DEF_W, int)
        assert theme.WINDOW_DEF_W == 1400

        assert isinstance(theme.WINDOW_DEF_H, int)
        assert theme.WINDOW_DEF_H == 900

        assert isinstance(theme.SPLITTER_SIZES, list)
        assert theme.SPLITTER_SIZES == [560, 840]

        assert isinstance(theme.TOAST_DURATION_MS, int)
        assert theme.TOAST_DURATION_MS == 4000
