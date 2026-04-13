# CRM AI MCP Server
**By MEOK AI Labs** | [meok.ai](https://meok.ai)

Customer relationship management toolkit: lead scoring, deal stage prediction, follow-up scheduling, customer health scoring, and churn prediction.

## Tools

| Tool | Description |
|------|-------------|
| `lead_scorer` | Score leads (0-100) based on firmographic and behavioral data |
| `deal_stage_predictor` | Predict deal win probability and estimated close date |
| `followup_scheduler` | Schedule follow-ups based on priority and engagement strategy |
| `customer_health_score` | Calculate customer health from usage, support, NPS, and adoption |
| `churn_predictor` | Predict churn probability with retention playbook recommendations |

## Installation

```bash
pip install mcp
```

## Usage

### Run the server

```bash
python server.py
```

### Claude Desktop config

```json
{
  "mcpServers": {
    "crm": {
      "command": "python",
      "args": ["/path/to/crm-ai-mcp/server.py"]
    }
  }
}
```

## Pricing

| Tier | Limit | Price |
|------|-------|-------|
| Free | 30 calls/day | $0 |
| Pro | Unlimited + premium features | $9/mo |
| Enterprise | Custom + SLA + support | Contact us |

## License

MIT
