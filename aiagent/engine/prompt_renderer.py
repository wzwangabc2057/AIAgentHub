"""
Prompt renderer - variable substitution + API callback injection

Responsibilities:
1. Replace template variables ({topic}, {input}, etc.)
2. Replace chain output references ({step_N_output})
3. Auto-inject API callback instructions (curl commands for /results and /executions/{id}/done)
"""

import re
from typing import Dict, Optional
from loguru import logger

from aiagent.config import settings


# Callback instruction template injected at the end of every prompt
CALLBACK_TEMPLATE = """

## 完成后必须执行

### 1. 存储结果（完成任务后调用）
curl -X POST {api_base}/api/results \\
  -H "Content-Type: application/json" \\
  -d '{{"execution_id": "{execution_id}", "agent_id": "{agent_id}", "step": {step}, "data": "你的完整输出结果（纯文本，不要包含JSON转义）"}}'

### 2. 报告完成（最后一步，必须调用！）
curl -X POST {api_base}/api/executions/{execution_id}/done

不要问问题，直接开始执行。完成后必须调用上面的接口。
"""


def render_prompt(
    template: str,
    variables: Dict[str, str],
    execution_id: str,
    agent_id: str,
    step: Optional[int] = None,
    step_outputs: Optional[Dict[int, str]] = None,
) -> str:
    """
    Render a prompt template with variables and inject callback instructions.

    Args:
        template: Prompt template content
        variables: User-provided variables
        execution_id: Current execution ID
        agent_id: Agent ID
        step: Step number in chain (None for single execution)
        step_outputs: Map of step_number -> output text for chain variable resolution
    """
    rendered = template

    # 1. Resolve chain step output references: {step_N_output}
    if step_outputs:
        for step_num, output in step_outputs.items():
            placeholder = f"{{step_{step_num}_output}}"
            rendered = rendered.replace(placeholder, output)

    # Also resolve step references in variable values
    resolved_vars = {}
    for key, value in variables.items():
        resolved_value = value
        if step_outputs:
            step_ref_pattern = re.compile(r'\{step_(\d+)_output\}')
            for match in step_ref_pattern.finditer(value):
                ref_step = int(match.group(1))
                if ref_step in step_outputs:
                    resolved_value = resolved_value.replace(match.group(0), step_outputs[ref_step])
        resolved_vars[key] = resolved_value

    # 2. Replace user variables
    for key, value in resolved_vars.items():
        rendered = rendered.replace(f"{{{key}}}", value)

    # 3. Inject API callback instructions
    api_base = settings.api_base_url.rstrip("/")
    callback = CALLBACK_TEMPLATE.format(
        api_base=api_base,
        execution_id=execution_id,
        agent_id=agent_id,
        step=step if step is not None else 0,
    )
    rendered += callback

    return rendered
