"""
Agent — orchestrates the LLM ↔ MCP-tool loop.

Flow:
  1. Build system prompt with persona + tool guidance
  2. Send user message (+ optional image/STL metadata) to LLM
  3. If LLM returns tool_calls → dispatch each, append results, loop
  4. Return final assistant text

Designed to be called from a QThread so the UI never blocks.
"""

import json
from typing import List, Optional, Callable

from .llm_client import LLMClient
from .tools_registry import TOOLS_SCHEMA, dispatch_tool
from ..utils.file_utils import encode_image_base64, is_stl_file, is_image_file, mime_type_for

MAX_TOOL_ROUNDS = 8  # safety cap on agentic loops

SYSTEM_PROMPT = """Ты — Aurora, интеллектуальный AI-ассистент для STE Slicer (3D/5D FDM-печать).

Твоя задача: получить описание задачи пользователя и **полностью автоматически** настроить параметры печати, выбрать режим (3D или 5D), загрузить модель и запустить слайсинг.

## Алгоритм работы
1. Если пользователь приложил STL — сначала вызови `analyze_geometry`.
2. Если упоминаются нагрузка / прочность / кронштейн / механическая деталь → обязательно вызови `analyze_stress` (киллер-фича: тепловая карта напряжений + адаптивное заполнение).
3. По результатам анализа вызови `load_and_orient_model` с оптимальной ориентацией из стресс-анализа.
4. Вызови `apply_full_profile` с подобранными параметрами.
5. Если есть зоны высокого напряжения — вызови `apply_adaptive_infill`.
6. Наконец, вызови `start_slicing`.
7. Дай пользователю краткое **объяснение каждого принятого решения** на русском языке.

## Правила подбора материала
- PLA: декоративные детали, прототипы, низкие нагрузки
- PETG: функциональные детали, умеренные нагрузки, влагостойкость  
- ABS: высокая температура, ударостойкость
- TPU: гибкие детали
- Nylon/PA: высокопрочные конструкции, шестерни

## Правила режима печати
- 5D: нависания > 45°, сложная геометрия, высокие механические требования
- 3D: простые детали, нет нависаний > 45°

## Стиль ответа
- Объясняй решения понятно, без технического жаргона
- Указывай конкретные цифры (температура, скорость, % заполнения)
- Упоминай экономию материала/времени если применялось адаптивное заполнение
- Отвечай на русском языке
"""


class Agent:
    def __init__(self):
        self.llm = LLMClient()

    def run(
        self,
        user_text: str,
        attached_files: Optional[List[str]] = None,
        on_tool_call: Optional[Callable[[str, dict], None]] = None,
    ) -> str:
        """
        Run the agent loop synchronously.

        :param user_text:      User's natural-language request.
        :param attached_files: List of file paths (STL or images).
        :param on_tool_call:   Optional callback(tool_name, args) for UI status updates.
        :return:               Final assistant reply text.
        """
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Build user message content (multimodal if images attached)
        content_parts = self._build_user_content(user_text, attached_files or [])
        messages.append({"role": "user", "content": content_parts})

        for _round in range(MAX_TOOL_ROUNDS):
            response = self.llm.chat_completion(messages, tools=TOOLS_SCHEMA)
            choice = response.choices[0]
            msg = choice.message

            # Append assistant turn (may contain tool_calls)
            messages.append(msg)

            if choice.finish_reason == "tool_calls" and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}

                    if on_tool_call:
                        on_tool_call(tool_name, args)

                    tool_result = dispatch_tool(tool_name, args)

                    messages.append({
                        "role":         "tool",
                        "tool_call_id": tc.id,
                        "content":      tool_result,
                    })
                # Loop: let LLM process tool results and decide next step
                continue

            # finish_reason == "stop" → final answer
            return msg.content or ""

        return "Агент завершил работу (достигнут лимит шагов)."

    # ─── Private helpers ──────────────────────────────────────────────────────

    def _build_user_content(self, text: str, files: List[str]):
        """
        Build the user message content list.
        - Text always included
        - Images → base64 image_url parts
        - STL files → text metadata note (LLM can then call analyze_geometry)
        """
        parts = [{"type": "text", "text": text}]

        stl_paths = []
        for path in files:
            if is_image_file(path):
                b64 = encode_image_base64(path)
                mime = mime_type_for(path)
                parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"},
                })
            elif is_stl_file(path):
                stl_paths.append(path)

        if stl_paths:
            stl_note = "\n\nПриложены STL-файлы:\n" + "\n".join(f"• {p}" for p in stl_paths)
            parts[0]["text"] += stl_note

        # If only one part (plain text, no images), return a plain string for
        # maximum API compatibility
        if len(parts) == 1:
            return parts[0]["text"]
        return parts
