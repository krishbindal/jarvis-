# Scheduled task execution evidence

Jarvis's autonomy engine may schedule a simple `open <app>` command and ask
the action registry to run it. The resulting `success: true` is the action
handler's own reported outcome, **not** independent proof of a focused window.

Other natural-language scheduled tasks are handed to the normal
`command_received` pipeline. Publishing an event does **not** mean the
downstream worker executed or completed the task.

- **One-off task**: `dispatched_unverified` after an event is emitted;
  `completed` only after a supported direct executor reports success;
  `failed` after an observed failure.
- **Recurring task**: retains `recurring` when dispatch was attempted;
  this is a schedule lifecycle state, not proof of a completed occurrence.
- **Already active app**: `skipped_active` for one-off requests; no new
  launch is claimed.
- **Compound command**: queued for the main planner instead of treating
  the entire instruction as an app name.

**Limitation:** The existing event-bus interface does not yet correlate a
scheduled task with its final downstream execution acknowledgment. A
follow-up improvement should record execution request IDs and reconcile
`dispatched_unverified` against genuine `command_result` callbacks.
Until then, do not report queued tasks as completed or calculate a
scheduled-task success rate from dispatch counts.
