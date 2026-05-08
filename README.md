<div align="center">

# Crm Ai MCP

**MCP server for crm ai mcp operations**

[![PyPI](https://img.shields.io/pypi/v/meok-crm-ai-mcp)](https://pypi.org/project/meok-crm-ai-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-MCP_Server-purple)](https://meok.ai)

</div>

## Overview

Crm Ai MCP provides AI-powered tools via the Model Context Protocol (MCP).

## Tools

| Tool | Description |
|------|-------------|
| `lead_scorer` | Score a sales lead (0-100) based on firmographic data, engagement signals, |
| `deal_stage_predictor` | Predict deal win probability and estimated close date based on |
| `followup_scheduler` | Schedule follow-ups for a list of contacts based on priority, |
| `customer_health_score` | Calculate a customer health score (0-100) from usage, support, NPS, |
| `churn_predictor` | Predict churn probability and recommend a retention playbook based on |

## Installation

```bash
pip install meok-crm-ai-mcp
```

## Usage with Claude Desktop

Add to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "crm-ai-mcp": {
      "command": "python",
      "args": ["-m", "meok_crm_ai_mcp.server"]
    }
  }
}
```

## Usage with FastMCP

```python
from mcp.server.fastmcp import FastMCP

# This server exposes 5 tool(s) via MCP
# See server.py for full implementation
```

## License

MIT © [MEOK AI Labs](https://meok.ai)
