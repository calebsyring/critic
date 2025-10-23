## Design Flowchart
- Below we can see a diagram that explains how the flask app will interact with the backend. All of the run check calls are performed on the AWS side per the lambda functions. The App only talks to the dynamo ddb via creating monitors or grabbing log information that is store via the lambda functions.
```mermaid
flowchart TD

subgraph UserSide[User Side]
    UI[Web UI] -->|REST calls| API[Flask API]
end

subgraph AWS[Backend AWS]
    API -->|Create / Update Monitors| DDB[(DynamoDB)]
    EB[EventBridge Scheduler] -->|Invoke| RunDueChecks[Lambda: run_due_checks]
    RunDueChecks -->|Query due monitors| DDB
    RunDueChecks -->|Invokes run_check after query due monitors| RunCheck[Lambda: run_check]
    RunCheck -->|Perform HTTP checks<br/>Evaluate assertions| Target[(External URLs)]
    RunCheck -->|Write results / logs| DDB
end

UI -->|Fetch status, logs| DDB

classDef lambda fill:#f6f8fa,stroke:#d4d4d4,color:#000,stroke-width:1px;
classDef aws fill:#f0fff4,stroke:#a3a3a3,color:#000,stroke-width:1px;
classDef user fill:#f0f8ff,stroke:#a3a3a3,color:#000,stroke-width:1px;

class RunDueChecks,RunCheck lambda;
class EB,DDB,Target aws;
class UI,API user;

```