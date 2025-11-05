# Table Research

### Overview:
- Project Table – stores information about projects that group monitors
- Uptime Monitor Table – stores monitor configurations and current state
- Uptime Log Table – stores logs of each check result for reporting and history


### Project Table:

| Field | Type | Description |
|--------|------|-------------|
| id | UUID | Unique project identifier (partition key) |
| name | String | This is the Project name |

**Here is an example of what it could look like:**

| id | name |
|----|------|
| `a12f...` | "Website Monitors" |
| `b45d...` | "API Watcher" |


### Uptime Monitor Table:

| Field | Type | Description |
|--------|------|-------------|
| project_id | UUID | Partition key referencing Project |
| id | UUID | Sort key (unique per monitor) |
| name | String | Monitor name |
| state | Enum | `new`, `up`, `down`, `paused` |
| url | String | Endpoint to check |
| frequency_mins | Number | How often to check (minutes) |
| next_due_at | Timestamp | When next check is scheduled |
| timeout_secs | Number | Request timeout (seconds) |
| alert_settings | JSON | Slack/email alert configuration |
| retry_config | JSON | Retry and realert intervals |

**Here is an example of what it could look like:**

| project_id | id | name | state | url | frequency_mins | next_due_at |
|-------------|----|------|--------|-----|----------------|-------------|
| `a12f...` | `m1...` | "Main Site" | up | https://example.com | 5 | 1730150400 |


### Uptime Log Table

| Field | Type | Description |
|--------|------|-------------|
| monitor_id | UUID | Partition key referencing Monitor |
| timestamp | Epoch Int | Sort key (check time) |
| status | Enum | `up` or `down` |
| resp_code | Number | HTTP response code |
| latency_secs | Number | Response latency in seconds |

**Here is an example of what it could look like:**

| monitor_id | timestamp | status | resp_code | latency_secs |
|-------------|------------|---------|------------|---------------|
| `m1...` | 1730150410 | up | 200 | 0.23 |
| `m1...` | 1730150700 | down | 500 | 1.02 |
| `m1...` | 1730150705 | down | 500 | 2.02 |

---

### 🧾 Summary

This document outlines the three main DynamoDB-style tables used for uptime tracking:
- **Project Table** holds high-level project data.
- **Uptime Monitor Table** defines each monitor’s configuration and operational state.
- **Uptime Log Table** records every individual check result for audit and analytics.

Together, these tables enable structured tracking, alerting, and performance reporting for monitored systems.
