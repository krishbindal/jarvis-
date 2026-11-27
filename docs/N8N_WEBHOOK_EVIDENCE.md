# n8n webhook execution evidence

Jarvis has two n8n entry points: `skill:automation` and `trigger_n8n`.
Both use the same configured-webhook URL validator and require explicit user
approval through the Jarvis action policy.

- External webhook URLs must use HTTPS. Explicit local loopback may use HTTP.
- Credentials embedded in URLs, invalid ports, fragments and redirects are
  rejected; the request does not follow a new destination.
- Request parameters are JSON-validated and bounded. Direct `trigger_n8n`
  responses are inspected within a 16-KiB size limit.
- HTTP 200/201/202/204 is **only a transport acknowledgment**, not proof that
  the workflow, smart-home device or external integration completed anything.
- A JSON body explicitly indicating `success: false` or a failed status is
  considered a rejection even if HTTP says 200.
- Downstream response text is untrusted and is not automatically passed to
  the next tool's target or shown as Jarvis's own completion statement.

Tests use fake HTTP responses with no real webhook calls. Real provider
credentials, workflows, smart-home equipment and external data still require
human-supervised integration checks. Never describe a transport acknowledgment
as a verified remote action or a measured completion rate.
