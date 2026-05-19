Feature: 'Limpar concluídas' button behavior (module-5/TASK-1/ST004)
  As a user
  I want the "Limpar concluídas" button to manage its enabled state correctly
  So that I can hide all completed tasks with one click

  Scenario: Button disabled by default
    Given a HeaderBar instance
    And the button is initially disabled
    Then the button should be disabled
    And the tooltip should say 'Nenhuma task concluída visível'

  Scenario: Button enabled when has visible done tasks
    Given a HeaderBar instance
    When the button is enabled with set_clear_done_enabled(True)
    Then the button should be enabled
    And the tooltip should say 'Ocultar tasks concluídas'

  Scenario: Clicking button emits signal and hides tasks
    Given a HeaderBar instance
    When the button is enabled with set_clear_done_enabled(True)
    And the button is clicked
    Then the clear_completed_clicked signal should be emitted

  Scenario: Error handling for database failures
    Given a HeaderBar instance
    When the repository mark_hidden() method fails
    Then the button should remain clickable
    And the tooltip should provide feedback
