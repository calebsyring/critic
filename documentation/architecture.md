# Model

## Project
The `Project` model represents a logical grouping for uptime monitors.

| Field | Type | Description |
|---|---|---|
| `id` | `uuid` | Partition key, unique identifier for the project. |
| `name` | `str` | Name of the project. |

## UptimeMonitor
The `UptimeMonitor` model defines a specific URL to be monitored and its associated configuration.

| Field | Type | Description |
|---|---|---|
| `project_id` | `uuid` | Partition key, links to the `Project` it belongs to. |
| `id` | `uuid` | Sort key, unique identifier for the monitor within a project. |
| `name` | `str` | Name of the uptime monitor. |
| `state` | `enum` | Current state of the monitor (`new`, `up`, `down`, `paused`). |
| `url` | `str` | The URL to be monitored. |
| `frequency_mins` | `int` | How often the monitor should run, in minutes (minimum 1 minute due to scheduler precision). |
| `next_due_at` | `int` or `str` | Timestamp (epoch int or ISO format string) when the next check is due. |
| `timeout_secs` | `int` | Timeout for the HTTP request in seconds. |
| `assertions` | `map` | Defines conditions to check against the HTTP response (e.g., `response.time`, `response.code`). Structure varies by field. Refer to Cronitor for available fields. |
| `failures_before_alerting` | `int` | Number of consecutive failures before an alert is triggered. |
| `alert_slack_channels` | `list<str>` | List of Slack channels to send alerts to. |
| `alert_emails` `list<str>` | List of email addresses to send alerts to. |
| `realert_interval_mins` | `int` | Minimum time in minutes between consecutive alerts for the same issue. |

## UptimeLog
The `UptimeLog` model stores the results of each individual uptime check.

| Field | Type | Description |
|---|---|---|
| `monitor_id` | `uuid` | Partition key, links to the `UptimeMonitor` this log belongs to. |
| `timestamp` | `int` | Sort key, epoch timestamp of when the check was performed. |
| `status` | `enum` | Result of the check (`up` or `down`). |
| `resp_code` | `int` | HTTP response code received. |
| `latency_secs` | `float` | Latency of the HTTP request in seconds (can represent milliseconds, as DynamoDB numbers are floats). |

# Lambda

## Web UI:
- Login (Level 12 oauth)
- Create project
  - User would copy the generated uuid and use that to make the `set_project_monitors` call below.
- Delete project
- Dashboard: List monitors by project w/ search
- Monitor page: show config and logs for monitor, (un)pause monitor

## API:
- `set_project_monitors`
  - **Endpoint:** `PUT /project/{project_id}/monitors`
  - **Structure:** `{'uptime': [MONITORS], 'job': [MONITORS]}` (currently only `uptime` monitors are supported).
  - **Validation:** The view validates monitor types and structure using Pydantic.
  - **Functionality:**
    - Adds new monitors.
    - Updates configuration for existing monitors.
    - Deletes missing monitors and their associated logs.
  - **Deletion Confirmation:** Requires explicit confirmation for monitor deletion.
  - **Authentication:** Requires knowledge of the correct project ID.

## Events (exposed functions called directly, bypassing the Flask API layer, use mu tasks):
- `run_due_checks`
  - Runs once a minute (scheduled in EventBridge)
  - Query all the monitors with `next_due_at` less than or equal to the minute we're running for and status != paused
  - Concurrently `run_check` with each monitor (as a lambda execution)
 - `run_check` (Lambda function)
   - make the request
   - check assertions
   - update monitor status
   - add log
   - alert as needed with false assertions (NOT as lambda executions, just python functions, nothing's waiting at this point; but may need to do some queuing/retrying for notification robustness)
   - make sure we respect realert inverval, may need to add another field to do that
   - update `next_due_at` - make sure it's an exact/rounded minute
## Design Flowchart
- Below we can see a diagram that explains how the flask app will interact with the backend. All of the run check calls are performed on the AWS side per the lambda functions. The App only talks to the dynamo ddb via creating monitors or grabbing log information that is store via the lambda functions.
```mermaid
flowchart TD

subgraph UserSide[User Side]
    UI[Web UI]
    API[Flask API]
end

subgraph AWS[Backend AWS]
    API -->|Create / Update Monitors| DDB[(DynamoDB)]
    EB[EventBridge Scheduler] -->|Invoke| RunDueChecks[Lambda: run_due_checks]
    RunDueChecks -->|Query due monitors| DDB
    RunDueChecks -->|Invokes run_check after query due monitors| RunCheck[Lambda: run_check]
    RunCheck -->|Perform HTTP checks<br/>Evaluate assertions| Target[(External URLs)]
    RunCheck -->|Write results / logs| DDB
    RunCheck --> SendAlerts[Notify third party on monitor failure]
end

subgraph ThirdParty[Slack or Email]

        SendAlerts --> Slack
        SendAlerts --> Email
end

UI -->|Fetch status, logs| DDB

classDef lambda fill:#f6f8fa,stroke:#d4d4d4,color:#000,stroke-width:1px;
classDef aws fill:#f0fff4,stroke:#a3a3a3,color:#000,stroke-width:1px;
classDef user fill:#f0f8ff,stroke:#a3a3a3,color:#000,stroke-width:1px;

class RunDueChecks,RunCheck lambda;
class EB,DDB,Target aws;
class UI,API user;

```
