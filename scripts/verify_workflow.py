from pprint import pprint
from uuid import uuid4

from aegisops.workflows.incident import incident_workflow


def main():
    state = {
        "incident_id": uuid4(),
        "title": "High CPU utilization detected",
        "severity": "high",
        "status": "open",
        "alert_name": "HighCPUUsage",
    }

    result = incident_workflow.invoke(state)
    pprint(result)


if __name__ == "__main__":
    main()
