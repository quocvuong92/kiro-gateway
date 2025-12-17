# -*- coding: utf-8 -*-

"""
Unit-тесты для конвертеров OpenAI <-> Kiro.
Проверяет логику преобразования форматов сообщений и payload.
"""

import pytest

from unittest.mock import patch

from kiro_gateway.converters import (
    extract_text_content,
    merge_adjacent_messages,
    build_kiro_history,
    build_kiro_payload,
    process_tools_with_long_descriptions,
    _extract_tool_results,
    _extract_tool_uses,
    _build_user_input_context
)
from kiro_gateway.models import ChatMessage, ChatCompletionRequest, Tool, ToolFunction


class TestExtractTextContent:
    """Тесты функции extract_text_content."""
    
    def test_extracts_from_string(self):
        """
        Что он делает: Проверяет извлечение текста из строки.
        Цель: Убедиться, что строка возвращается как есть.
        """
        print("Настройка: Простая строка...")
        content = "Hello, World!"
        
        print("Действие: Извлечение текста...")
        result = extract_text_content(content)
        
        print(f"Сравниваем результат: Ожидалось 'Hello, World!', Получено '{result}'")
        assert result == "Hello, World!"
    
    def test_extracts_from_none(self):
        """
        Что он делает: Проверяет обработку None.
        Цель: Убедиться, что None возвращает пустую строку.
        """
        print("Настройка: None...")
        
        print("Действие: Извлечение текста...")
        result = extract_text_content(None)
        
        print(f"Сравниваем результат: Ожидалось '', Получено '{result}'")
        assert result == ""
    
    def test_extracts_from_list_with_text_type(self):
        """
        Что он делает: Проверяет извлечение из списка с type=text.
        Цель: Убедиться, что OpenAI multimodal формат обрабатывается.
        """
        print("Настройка: Список с type=text...")
        content = [
            {"type": "text", "text": "Hello"},
            {"type": "text", "text": " World"}
        ]
        
        print("Действие: Извлечение текста...")
        result = extract_text_content(content)
        
        print(f"Сравниваем результат: Ожидалось 'Hello World', Получено '{result}'")
        assert result == "Hello World"
    
    def test_extracts_from_list_with_text_key(self):
        """
        Что он делает: Проверяет извлечение из списка с ключом text.
        Цель: Убедиться, что альтернативный формат обрабатывается.
        """
        print("Настройка: Список с ключом text...")
        content = [{"text": "Hello"}, {"text": " World"}]
        
        print("Действие: Извлечение текста...")
        result = extract_text_content(content)
        
        print(f"Сравниваем результат: Ожидалось 'Hello World', Получено '{result}'")
        assert result == "Hello World"
    
    def test_extracts_from_list_with_strings(self):
        """
        Что он делает: Проверяет извлечение из списка строк.
        Цель: Убедиться, что список строк объединяется.
        """
        print("Настройка: Список строк...")
        content = ["Hello", " ", "World"]
        
        print("Действие: Извлечение текста...")
        result = extract_text_content(content)
        
        print(f"Сравниваем результат: Ожидалось 'Hello World', Получено '{result}'")
        assert result == "Hello World"
    
    def test_extracts_from_mixed_list(self):
        """
        Что он делает: Проверяет извлечение из смешанного списка.
        Цель: Убедиться, что разные форматы в одном списке обрабатываются.
        """
        print("Настройка: Смешанный список...")
        content = [
            {"type": "text", "text": "Part1"},
            "Part2",
            {"text": "Part3"}
        ]
        
        print("Действие: Извлечение текста...")
        result = extract_text_content(content)
        
        print(f"Сравниваем результат: Ожидалось 'Part1Part2Part3', Получено '{result}'")
        assert result == "Part1Part2Part3"
    
    def test_converts_other_types_to_string(self):
        """
        Что он делает: Проверяет конвертацию других типов в строку.
        Цель: Убедиться, что числа и другие типы преобразуются.
        """
        print("Настройка: Число...")
        content = 42
        
        print("Действие: Извлечение текста...")
        result = extract_text_content(content)
        
        print(f"Сравниваем результат: Ожидалось '42', Получено '{result}'")
        assert result == "42"
    
    def test_handles_empty_list(self):
        """
        Что он делает: Проверяет обработку пустого списка.
        Цель: Убедиться, что пустой список возвращает пустую строку.
        """
        print("Настройка: Пустой список...")
        content = []
        
        print("Действие: Извлечение текста...")
        result = extract_text_content(content)
        
        print(f"Сравниваем результат: Ожидалось '', Получено '{result}'")
        assert result == ""


class TestMergeAdjacentMessages:
    """Тесты функции merge_adjacent_messages."""
    
    def test_merges_adjacent_user_messages(self):
        """
        Что он делает: Проверяет объединение соседних user сообщений.
        Цель: Убедиться, что сообщения с одинаковой ролью объединяются.
        """
        print("Настройка: Два user сообщения подряд...")
        messages = [
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="user", content="World")
        ]
        
        print("Действие: Объединение сообщений...")
        result = merge_adjacent_messages(messages)
        
        print(f"Сравниваем длину: Ожидалось 1, Получено {len(result)}")
        assert len(result) == 1
        assert "Hello" in result[0].content
        assert "World" in result[0].content
    
    def test_preserves_alternating_messages(self):
        """
        Что он делает: Проверяет сохранение чередующихся сообщений.
        Цель: Убедиться, что разные роли не объединяются.
        """
        print("Настройка: Чередующиеся сообщения...")
        messages = [
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi"),
            ChatMessage(role="user", content="How are you?")
        ]
        
        print("Действие: Объединение сообщений...")
        result = merge_adjacent_messages(messages)
        
        print(f"Сравниваем длину: Ожидалось 3, Получено {len(result)}")
        assert len(result) == 3
    
    def test_handles_empty_list(self):
        """
        Что он делает: Проверяет обработку пустого списка.
        Цель: Убедиться, что пустой список не вызывает ошибок.
        """
        print("Настройка: Пустой список...")
        
        print("Действие: Объединение сообщений...")
        result = merge_adjacent_messages([])
        
        print(f"Сравниваем результат: Ожидалось [], Получено {result}")
        assert result == []
    
    def test_handles_single_message(self):
        """
        Что он делает: Проверяет обработку одного сообщения.
        Цель: Убедиться, что одно сообщение возвращается как есть.
        """
        print("Настройка: Одно сообщение...")
        messages = [ChatMessage(role="user", content="Hello")]
        
        print("Действие: Объединение сообщений...")
        result = merge_adjacent_messages(messages)
        
        print(f"Сравниваем длину: Ожидалось 1, Получено {len(result)}")
        assert len(result) == 1
        assert result[0].content == "Hello"
    
    def test_merges_multiple_adjacent_groups(self):
        """
        Что он делает: Проверяет объединение нескольких групп.
        Цель: Убедиться, что несколько групп соседних сообщений объединяются.
        """
        print("Настройка: Несколько групп соседних сообщений...")
        messages = [
            ChatMessage(role="user", content="A"),
            ChatMessage(role="user", content="B"),
            ChatMessage(role="assistant", content="C"),
            ChatMessage(role="assistant", content="D"),
            ChatMessage(role="user", content="E")
        ]
        
        print("Действие: Объединение сообщений...")
        result = merge_adjacent_messages(messages)
        
        print(f"Сравниваем длину: Ожидалось 3, Получено {len(result)}")
        assert len(result) == 3
        assert result[0].role == "user"
        assert result[1].role == "assistant"
        assert result[2].role == "user"
    
    def test_converts_tool_message_to_user_with_tool_result(self):
        """
        Что он делает: Проверяет преобразование tool message в user message с tool_result.
        Цель: Убедиться, что role="tool" преобразуется в user message с tool_results content.
        """
        print("Настройка: Tool message...")
        messages = [
            ChatMessage(role="tool", content="Tool result text", tool_call_id="call_123")
        ]
        
        print("Действие: Объединение сообщений...")
        result = merge_adjacent_messages(messages)
        
        print(f"Результат: {result}")
        print(f"Сравниваем длину: Ожидалось 1, Получено {len(result)}")
        assert len(result) == 1
        assert result[0].role == "user"
        
        print("Проверяем content содержит tool_result...")
        assert isinstance(result[0].content, list)
        assert len(result[0].content) == 1
        assert result[0].content[0]["type"] == "tool_result"
        assert result[0].content[0]["tool_use_id"] == "call_123"
        assert result[0].content[0]["content"] == "Tool result text"
    
    def test_converts_multiple_tool_messages_to_single_user_message(self):
        """
        Что он делает: Проверяет объединение нескольких tool messages в один user message.
        Цель: Убедиться, что несколько tool results объединяются в один user message.
        """
        print("Настройка: Несколько tool messages подряд...")
        messages = [
            ChatMessage(role="tool", content="Result 1", tool_call_id="call_1"),
            ChatMessage(role="tool", content="Result 2", tool_call_id="call_2"),
            ChatMessage(role="tool", content="Result 3", tool_call_id="call_3")
        ]
        
        print("Действие: Объединение сообщений...")
        result = merge_adjacent_messages(messages)
        
        print(f"Результат: {result}")
        print(f"Сравниваем длину: Ожидалось 1, Получено {len(result)}")
        assert len(result) == 1
        assert result[0].role == "user"
        
        print("Проверяем content содержит все tool_results...")
        assert isinstance(result[0].content, list)
        assert len(result[0].content) == 3
        
        tool_use_ids = [item["tool_use_id"] for item in result[0].content]
        assert "call_1" in tool_use_ids
        assert "call_2" in tool_use_ids
        assert "call_3" in tool_use_ids
    
    def test_tool_message_followed_by_user_message(self):
        """
        Что он делает: Проверяет tool message перед user message.
        Цель: Убедиться, что tool results и user message объединяются.
        """
        print("Настройка: Tool message + user message...")
        messages = [
            ChatMessage(role="tool", content="Tool result", tool_call_id="call_1"),
            ChatMessage(role="user", content="Continue please")
        ]
        
        print("Действие: Объединение сообщений...")
        result = merge_adjacent_messages(messages)
        
        print(f"Результат: {result}")
        print(f"Сравниваем длину: Ожидалось 1, Получено {len(result)}")
        # Tool message преобразуется в user, затем объединяется с user
        assert len(result) == 1
        assert result[0].role == "user"
    
    def test_assistant_tool_user_sequence(self):
        """
        Что он делает: Проверяет последовательность assistant -> tool -> user.
        Цель: Убедиться, что tool message корректно вставляется между assistant и user.
        """
        print("Настройка: assistant -> tool -> user...")
        messages = [
            ChatMessage(role="assistant", content="I'll call a tool"),
            ChatMessage(role="tool", content="Tool output", tool_call_id="call_abc"),
            ChatMessage(role="user", content="Thanks!")
        ]
        
        print("Действие: Объединение сообщений...")
        result = merge_adjacent_messages(messages)
        
        print(f"Результат: {result}")
        # assistant остаётся, tool+user объединяются в один user
        assert len(result) == 2
        assert result[0].role == "assistant"
        assert result[1].role == "user"
    
    def test_tool_message_with_empty_content(self):
        """
        Что он делает: Проверяет tool message с пустым content.
        Цель: Убедиться, что пустой результат заменяется на "(empty result)".
        """
        print("Настройка: Tool message с пустым content...")
        messages = [
            ChatMessage(role="tool", content="", tool_call_id="call_empty")
        ]
        
        print("Действие: Объединение сообщений...")
        result = merge_adjacent_messages(messages)
        
        print(f"Результат: {result}")
        assert len(result) == 1
        assert result[0].content[0]["content"] == "(empty result)"
    
    def test_tool_message_with_none_tool_call_id(self):
        """
        Что он делает: Проверяет tool message без tool_call_id.
        Цель: Убедиться, что отсутствующий tool_call_id заменяется на пустую строку.
        """
        print("Настройка: Tool message без tool_call_id...")
        messages = [
            ChatMessage(role="tool", content="Result", tool_call_id=None)
        ]
        
        print("Действие: Объединение сообщений...")
        result = merge_adjacent_messages(messages)
        
        print(f"Результат: {result}")
        assert len(result) == 1
        assert result[0].content[0]["tool_use_id"] == ""
    
    def test_merges_list_contents_correctly(self):
        """
        Что он делает: Проверяет объединение list contents.
        Цель: Убедиться, что списки объединяются корректно.
        """
        print("Настройка: Два user сообщения с list content...")
        messages = [
            ChatMessage(role="user", content=[{"type": "text", "text": "Part 1"}]),
            ChatMessage(role="user", content=[{"type": "text", "text": "Part 2"}])
        ]
        
        print("Действие: Объединение сообщений...")
        result = merge_adjacent_messages(messages)
        
        print(f"Результат: {result}")
        assert len(result) == 1
        assert isinstance(result[0].content, list)
        assert len(result[0].content) == 2
    
    def test_merges_adjacent_assistant_tool_calls(self):
        """
        Что он делает: Проверяет объединение tool_calls при merge соседних assistant сообщений.
        Цель: Убедиться, что tool_calls из всех assistant сообщений сохраняются при объединении.
        
        Это критический тест для бага, когда Codex CLI отправляет несколько assistant
        сообщений подряд, каждое со своим tool_call. Без этого фикса второй tool_call
        терялся, что приводило к ошибке 400 от Kiro API (toolResult без toolUse).
        """
        print("Настройка: Два assistant сообщения с разными tool_calls...")
        messages = [
            ChatMessage(
                role="assistant",
                content=None,
                tool_calls=[{
                    "id": "tooluse_first",
                    "type": "function",
                    "function": {
                        "name": "shell",
                        "arguments": '{"command": ["ls", "-la"]}'
                    }
                }]
            ),
            ChatMessage(
                role="assistant",
                content=None,
                tool_calls=[{
                    "id": "tooluse_second",
                    "type": "function",
                    "function": {
                        "name": "shell",
                        "arguments": '{"command": ["pwd"]}'
                    }
                }]
            )
        ]
        
        print("Действие: Объединение сообщений...")
        result = merge_adjacent_messages(messages)
        
        print(f"Результат: {result}")
        print(f"Сравниваем длину: Ожидалось 1, Получено {len(result)}")
        assert len(result) == 1
        assert result[0].role == "assistant"
        
        print("Проверяем, что оба tool_calls сохранены...")
        assert result[0].tool_calls is not None
        print(f"Сравниваем количество tool_calls: Ожидалось 2, Получено {len(result[0].tool_calls)}")
        assert len(result[0].tool_calls) == 2
        
        tool_ids = [tc["id"] for tc in result[0].tool_calls]
        print(f"Tool IDs: {tool_ids}")
        assert "tooluse_first" in tool_ids
        assert "tooluse_second" in tool_ids
    
    def test_merges_three_adjacent_assistant_tool_calls(self):
        """
        Что он делает: Проверяет объединение tool_calls из трёх assistant сообщений.
        Цель: Убедиться, что все tool_calls сохраняются при объединении более двух сообщений.
        """
        print("Настройка: Три assistant сообщения с tool_calls...")
        messages = [
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=[{"id": "call_1", "type": "function", "function": {"name": "tool1", "arguments": "{}"}}]
            ),
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=[{"id": "call_2", "type": "function", "function": {"name": "tool2", "arguments": "{}"}}]
            ),
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=[{"id": "call_3", "type": "function", "function": {"name": "tool3", "arguments": "{}"}}]
            )
        ]
        
        print("Действие: Объединение сообщений...")
        result = merge_adjacent_messages(messages)
        
        print(f"Результат: {result}")
        assert len(result) == 1
        assert len(result[0].tool_calls) == 3
        
        tool_ids = [tc["id"] for tc in result[0].tool_calls]
        print(f"Сравниваем tool IDs: Ожидалось ['call_1', 'call_2', 'call_3'], Получено {tool_ids}")
        assert tool_ids == ["call_1", "call_2", "call_3"]
    
    def test_merges_assistant_with_and_without_tool_calls(self):
        """
        Что он делает: Проверяет объединение assistant с tool_calls и без.
        Цель: Убедиться, что tool_calls корректно инициализируются при объединении.
        """
        print("Настройка: Assistant без tool_calls + assistant с tool_calls...")
        messages = [
            ChatMessage(role="assistant", content="Thinking...", tool_calls=None),
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=[{"id": "call_1", "type": "function", "function": {"name": "tool1", "arguments": "{}"}}]
            )
        ]
        
        print("Действие: Объединение сообщений...")
        result = merge_adjacent_messages(messages)
        
        print(f"Результат: {result}")
        assert len(result) == 1
        assert result[0].tool_calls is not None
        print(f"Сравниваем количество tool_calls: Ожидалось 1, Получено {len(result[0].tool_calls)}")
        assert len(result[0].tool_calls) == 1
        assert result[0].tool_calls[0]["id"] == "call_1"


class TestBuildKiroHistory:
    """Тесты функции build_kiro_history."""
    
    def test_builds_user_message(self):
        """
        Что он делает: Проверяет построение user сообщения.
        Цель: Убедиться, что user сообщение преобразуется в userInputMessage.
        """
        print("Настройка: User сообщение...")
        messages = [ChatMessage(role="user", content="Hello")]
        
        print("Действие: Построение истории...")
        result = build_kiro_history(messages, "claude-sonnet-4")
        
        print(f"Результат: {result}")
        assert len(result) == 1
        assert "userInputMessage" in result[0]
        assert result[0]["userInputMessage"]["content"] == "Hello"
        assert result[0]["userInputMessage"]["modelId"] == "claude-sonnet-4"
    
    def test_builds_assistant_message(self):
        """
        Что он делает: Проверяет построение assistant сообщения.
        Цель: Убедиться, что assistant сообщение преобразуется в assistantResponseMessage.
        """
        print("Настройка: Assistant сообщение...")
        messages = [ChatMessage(role="assistant", content="Hi there")]
        
        print("Действие: Построение истории...")
        result = build_kiro_history(messages, "claude-sonnet-4")
        
        print(f"Результат: {result}")
        assert len(result) == 1
        assert "assistantResponseMessage" in result[0]
        assert result[0]["assistantResponseMessage"]["content"] == "Hi there"
    
    def test_ignores_system_messages(self):
        """
        Что он делает: Проверяет игнорирование system сообщений.
        Цель: Убедиться, что system сообщения не добавляются в историю.
        """
        print("Настройка: System сообщение...")
        messages = [ChatMessage(role="system", content="You are helpful")]
        
        print("Действие: Построение истории...")
        result = build_kiro_history(messages, "claude-sonnet-4")
        
        print(f"Сравниваем длину: Ожидалось 0, Получено {len(result)}")
        assert len(result) == 0
    
    def test_builds_conversation_history(self):
        """
        Что он делает: Проверяет построение полной истории разговора.
        Цель: Убедиться, что чередование user/assistant сохраняется.
        """
        print("Настройка: Полная история разговора...")
        messages = [
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi"),
            ChatMessage(role="user", content="How are you?")
        ]
        
        print("Действие: Построение истории...")
        result = build_kiro_history(messages, "claude-sonnet-4")
        
        print(f"Результат: {result}")
        assert len(result) == 3
        assert "userInputMessage" in result[0]
        assert "assistantResponseMessage" in result[1]
        assert "userInputMessage" in result[2]
    
    def test_handles_empty_list(self):
        """
        Что он делает: Проверяет обработку пустого списка.
        Цель: Убедиться, что пустой список возвращает пустую историю.
        """
        print("Настройка: Пустой список...")
        
        print("Действие: Построение истории...")
        result = build_kiro_history([], "claude-sonnet-4")
        
        print(f"Сравниваем результат: Ожидалось [], Получено {result}")
        assert result == []


class TestExtractToolResults:
    """Тесты функции _extract_tool_results."""
    
    def test_extracts_tool_results_from_list(self):
        """
        Что он делает: Проверяет извлечение tool results из списка.
        Цель: Убедиться, что tool_result элементы извлекаются.
        """
        print("Настройка: Список с tool_result...")
        content = [
            {"type": "tool_result", "tool_use_id": "call_123", "content": "Result text"}
        ]
        
        print("Действие: Извлечение tool results...")
        result = _extract_tool_results(content)
        
        print(f"Результат: {result}")
        assert len(result) == 1
        assert result[0]["toolUseId"] == "call_123"
        assert result[0]["status"] == "success"
    
    def test_returns_empty_for_string_content(self):
        """
        Что он делает: Проверяет возврат пустого списка для строки.
        Цель: Убедиться, что строка не содержит tool results.
        """
        print("Настройка: Строка...")
        content = "Just a string"
        
        print("Действие: Извлечение tool results...")
        result = _extract_tool_results(content)
        
        print(f"Сравниваем результат: Ожидалось [], Получено {result}")
        assert result == []
    
    def test_returns_empty_for_list_without_tool_results(self):
        """
        Что он делает: Проверяет возврат пустого списка без tool_result.
        Цель: Убедиться, что обычные элементы не извлекаются.
        """
        print("Настройка: Список без tool_result...")
        content = [{"type": "text", "text": "Hello"}]
        
        print("Действие: Извлечение tool results...")
        result = _extract_tool_results(content)
        
        print(f"Сравниваем результат: Ожидалось [], Получено {result}")
        assert result == []


class TestExtractToolUses:
    """Тесты функции _extract_tool_uses."""
    
    def test_extracts_from_tool_calls_field(self):
        """
        Что он делает: Проверяет извлечение из поля tool_calls.
        Цель: Убедиться, что OpenAI tool_calls формат обрабатывается.
        """
        print("Настройка: Сообщение с tool_calls...")
        msg = ChatMessage(
            role="assistant",
            content="",
            tool_calls=[{
                "id": "call_123",
                "function": {
                    "name": "get_weather",
                    "arguments": '{"location": "Moscow"}'
                }
            }]
        )
        
        print("Действие: Извлечение tool uses...")
        result = _extract_tool_uses(msg)
        
        print(f"Результат: {result}")
        assert len(result) == 1
        assert result[0]["name"] == "get_weather"
        assert result[0]["toolUseId"] == "call_123"
    
    def test_extracts_from_content_list(self):
        """
        Что он делает: Проверяет извлечение из content списка.
        Цель: Убедиться, что tool_use в content обрабатывается.
        """
        print("Настройка: Сообщение с tool_use в content...")
        msg = ChatMessage(
            role="assistant",
            content=[{
                "type": "tool_use",
                "id": "call_456",
                "name": "search",
                "input": {"query": "test"}
            }]
        )
        
        print("Действие: Извлечение tool uses...")
        result = _extract_tool_uses(msg)
        
        print(f"Результат: {result}")
        assert len(result) == 1
        assert result[0]["name"] == "search"
        assert result[0]["toolUseId"] == "call_456"
    
    def test_returns_empty_for_no_tool_uses(self):
        """
        Что он делает: Проверяет возврат пустого списка без tool uses.
        Цель: Убедиться, что обычное сообщение не содержит tool uses.
        """
        print("Настройка: Обычное сообщение...")
        msg = ChatMessage(role="assistant", content="Hello")
        
        print("Действие: Извлечение tool uses...")
        result = _extract_tool_uses(msg)
        
        print(f"Сравниваем результат: Ожидалось [], Получено {result}")
        assert result == []


class TestProcessToolsWithLongDescriptions:
    """Тесты функции process_tools_with_long_descriptions."""
    
    def test_returns_none_and_empty_string_for_none_tools(self):
        """
        Что он делает: Проверяет обработку None вместо списка tools.
        Цель: Убедиться, что None возвращает (None, "").
        """
        print("Настройка: None вместо tools...")
        
        print("Действие: Обработка tools...")
        processed, doc = process_tools_with_long_descriptions(None)
        
        print(f"Сравниваем результат: Ожидалось (None, ''), Получено ({processed}, '{doc}')")
        assert processed is None
        assert doc == ""
    
    def test_returns_none_and_empty_string_for_empty_list(self):
        """
        Что он делает: Проверяет обработку пустого списка tools.
        Цель: Убедиться, что пустой список возвращает (None, "").
        """
        print("Настройка: Пустой список tools...")
        
        print("Действие: Обработка tools...")
        processed, doc = process_tools_with_long_descriptions([])
        
        print(f"Сравниваем результат: Ожидалось (None, ''), Получено ({processed}, '{doc}')")
        assert processed is None
        assert doc == ""
    
    def test_short_description_unchanged(self):
        """
        Что он делает: Проверяет, что короткие descriptions не изменяются.
        Цель: Убедиться, что tools с короткими descriptions остаются как есть.
        """
        print("Настройка: Tool с коротким description...")
        tools = [Tool(
            type="function",
            function=ToolFunction(
                name="get_weather",
                description="Get weather for a location",
                parameters={"type": "object", "properties": {}}
            )
        )]
        
        print("Действие: Обработка tools...")
        with patch('kiro_gateway.converters.TOOL_DESCRIPTION_MAX_LENGTH', 10000):
            processed, doc = process_tools_with_long_descriptions(tools)
        
        print(f"Сравниваем description: Ожидалось 'Get weather for a location', Получено '{processed[0].function.description}'")
        assert len(processed) == 1
        assert processed[0].function.description == "Get weather for a location"
        assert doc == ""
    
    def test_long_description_moved_to_system_prompt(self):
        """
        Что он делает: Проверяет перенос длинного description в system prompt.
        Цель: Убедиться, что длинные descriptions переносятся корректно.
        """
        print("Настройка: Tool с очень длинным description...")
        long_description = "A" * 15000  # 15000 символов - больше лимита
        tools = [Tool(
            type="function",
            function=ToolFunction(
                name="bash",
                description=long_description,
                parameters={"type": "object", "properties": {"command": {"type": "string"}}}
            )
        )]
        
        print("Действие: Обработка tools с лимитом 10000...")
        with patch('kiro_gateway.converters.TOOL_DESCRIPTION_MAX_LENGTH', 10000):
            processed, doc = process_tools_with_long_descriptions(tools)
        
        print(f"Проверяем reference в description...")
        assert len(processed) == 1
        assert "[Full documentation in system prompt under '## Tool: bash']" in processed[0].function.description
        
        print(f"Проверяем документацию в system prompt...")
        assert "## Tool: bash" in doc
        assert long_description in doc
        assert "# Tool Documentation" in doc
    
    def test_mixed_short_and_long_descriptions(self):
        """
        Что он делает: Проверяет обработку смешанного списка tools.
        Цель: Убедиться, что короткие остаются, длинные переносятся.
        """
        print("Настройка: Два tools - короткий и длинный...")
        short_desc = "Short description"
        long_desc = "B" * 15000
        tools = [
            Tool(
                type="function",
                function=ToolFunction(
                    name="short_tool",
                    description=short_desc,
                    parameters={}
                )
            ),
            Tool(
                type="function",
                function=ToolFunction(
                    name="long_tool",
                    description=long_desc,
                    parameters={}
                )
            )
        ]
        
        print("Действие: Обработка tools...")
        with patch('kiro_gateway.converters.TOOL_DESCRIPTION_MAX_LENGTH', 10000):
            processed, doc = process_tools_with_long_descriptions(tools)
        
        print(f"Проверяем количество tools: Ожидалось 2, Получено {len(processed)}")
        assert len(processed) == 2
        
        print(f"Проверяем короткий tool...")
        assert processed[0].function.description == short_desc
        
        print(f"Проверяем длинный tool...")
        assert "[Full documentation in system prompt" in processed[1].function.description
        assert "## Tool: long_tool" in doc
        assert long_desc in doc
    
    def test_preserves_tool_parameters(self):
        """
        Что он делает: Проверяет сохранение parameters при переносе description.
        Цель: Убедиться, что parameters не теряются.
        """
        print("Настройка: Tool с parameters и длинным description...")
        params = {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"},
                "units": {"type": "string", "enum": ["celsius", "fahrenheit"]}
            },
            "required": ["location"]
        }
        tools = [Tool(
            type="function",
            function=ToolFunction(
                name="weather",
                description="C" * 15000,
                parameters=params
            )
        )]
        
        print("Действие: Обработка tools...")
        with patch('kiro_gateway.converters.TOOL_DESCRIPTION_MAX_LENGTH', 10000):
            processed, doc = process_tools_with_long_descriptions(tools)
        
        print(f"Проверяем сохранение parameters...")
        assert processed[0].function.parameters == params
    
    def test_disabled_when_limit_is_zero(self):
        """
        Что он делает: Проверяет отключение функции при лимите 0.
        Цель: Убедиться, что при TOOL_DESCRIPTION_MAX_LENGTH=0 tools не изменяются.
        """
        print("Настройка: Tool с длинным description и лимит 0...")
        long_desc = "D" * 15000
        tools = [Tool(
            type="function",
            function=ToolFunction(
                name="test_tool",
                description=long_desc,
                parameters={}
            )
        )]
        
        print("Действие: Обработка tools с лимитом 0...")
        with patch('kiro_gateway.converters.TOOL_DESCRIPTION_MAX_LENGTH', 0):
            processed, doc = process_tools_with_long_descriptions(tools)
        
        print(f"Проверяем, что description не изменился...")
        assert processed[0].function.description == long_desc
        assert doc == ""
    
    def test_non_function_tools_unchanged(self):
        """
        Что он делает: Проверяет, что non-function tools не изменяются.
        Цель: Убедиться, что только function tools обрабатываются.
        """
        print("Настройка: Tool с type != function...")
        # Создаём tool с другим типом (хотя в реальности OpenAI поддерживает только function)
        tools = [Tool(
            type="other_type",
            function=ToolFunction(
                name="test",
                description="E" * 15000,
                parameters={}
            )
        )]
        
        print("Действие: Обработка tools...")
        with patch('kiro_gateway.converters.TOOL_DESCRIPTION_MAX_LENGTH', 10000):
            processed, doc = process_tools_with_long_descriptions(tools)
        
        print(f"Проверяем, что tool не изменился...")
        assert len(processed) == 1
        assert processed[0].type == "other_type"
        assert doc == ""
    
    def test_multiple_long_descriptions_all_moved(self):
        """
        Что он делает: Проверяет перенос нескольких длинных descriptions.
        Цель: Убедиться, что все длинные descriptions переносятся.
        """
        print("Настройка: Три tools с длинными descriptions...")
        tools = [
            Tool(type="function", function=ToolFunction(name="tool1", description="F" * 15000, parameters={})),
            Tool(type="function", function=ToolFunction(name="tool2", description="G" * 15000, parameters={})),
            Tool(type="function", function=ToolFunction(name="tool3", description="H" * 15000, parameters={}))
        ]
        
        print("Действие: Обработка tools...")
        with patch('kiro_gateway.converters.TOOL_DESCRIPTION_MAX_LENGTH', 10000):
            processed, doc = process_tools_with_long_descriptions(tools)
        
        print(f"Проверяем все три tools...")
        assert len(processed) == 3
        for i, tool in enumerate(processed):
            assert "[Full documentation in system prompt" in tool.function.description
        
        print(f"Проверяем документацию содержит все три секции...")
        assert "## Tool: tool1" in doc
        assert "## Tool: tool2" in doc
        assert "## Tool: tool3" in doc
    
    def test_empty_description_unchanged(self):
        """
        Что он делает: Проверяет обработку пустого description.
        Цель: Убедиться, что пустой description не вызывает ошибок.
        """
        print("Настройка: Tool с пустым description...")
        tools = [Tool(
            type="function",
            function=ToolFunction(
                name="empty_desc_tool",
                description="",
                parameters={}
            )
        )]
        
        print("Действие: Обработка tools...")
        with patch('kiro_gateway.converters.TOOL_DESCRIPTION_MAX_LENGTH', 10000):
            processed, doc = process_tools_with_long_descriptions(tools)
        
        print(f"Проверяем, что пустой description остался пустым...")
        assert processed[0].function.description == ""
        assert doc == ""
    
    def test_none_description_unchanged(self):
        """
        Что он делает: Проверяет обработку None description.
        Цель: Убедиться, что None description не вызывает ошибок.
        """
        print("Настройка: Tool с None description...")
        tools = [Tool(
            type="function",
            function=ToolFunction(
                name="none_desc_tool",
                description=None,
                parameters={}
            )
        )]
        
        print("Действие: Обработка tools...")
        with patch('kiro_gateway.converters.TOOL_DESCRIPTION_MAX_LENGTH', 10000):
            processed, doc = process_tools_with_long_descriptions(tools)
        
        print(f"Проверяем, что None description обработан корректно...")
        # None должен остаться None или стать пустой строкой
        assert processed[0].function.description is None or processed[0].function.description == ""
        assert doc == ""


class TestBuildUserInputContext:
    """Тесты функции _build_user_input_context."""
    
    def test_builds_tools_context(self):
        """
        Что он делает: Проверяет построение контекста с tools.
        Цель: Убедиться, что tools преобразуются в toolSpecification.
        """
        print("Настройка: Запрос с tools...")
        request = ChatCompletionRequest(
            model="claude-sonnet-4",
            messages=[ChatMessage(role="user", content="Hello")],
            tools=[Tool(
                type="function",
                function=ToolFunction(
                    name="get_weather",
                    description="Get weather",
                    parameters={"type": "object", "properties": {}}
                )
            )]
        )
        current_msg = ChatMessage(role="user", content="Hello")
        
        print("Действие: Построение контекста...")
        result = _build_user_input_context(request, current_msg)
        
        print(f"Результат: {result}")
        assert "tools" in result
        assert len(result["tools"]) == 1
        assert result["tools"][0]["toolSpecification"]["name"] == "get_weather"
    
    def test_returns_empty_for_no_tools(self):
        """
        Что он делает: Проверяет возврат пустого контекста без tools.
        Цель: Убедиться, что запрос без tools возвращает пустой контекст.
        """
        print("Настройка: Запрос без tools...")
        request = ChatCompletionRequest(
            model="claude-sonnet-4",
            messages=[ChatMessage(role="user", content="Hello")]
        )
        current_msg = ChatMessage(role="user", content="Hello")
        
        print("Действие: Построение контекста...")
        result = _build_user_input_context(request, current_msg)
        
        print(f"Сравниваем результат: Ожидалось {{}}, Получено {result}")
        assert result == {}


class TestBuildKiroPayloadToolCallsIntegration:
    """
    Интеграционные тесты для build_kiro_payload с tool_calls.
    Проверяет полный flow от OpenAI формата до Kiro формата.
    """
    
    def test_multiple_assistant_tool_calls_with_results(self):
        """
        Что он делает: Проверяет полный сценарий с несколькими assistant tool_calls и их результатами.
        Цель: Убедиться, что все toolUses и toolResults корректно связываются в Kiro payload.
        
        Это интеграционный тест для бага Codex CLI, где несколько assistant сообщений
        с tool_calls отправлялись подряд, а затем tool results. Без фикса второй toolUse
        терялся, что приводило к ошибке 400 от Kiro API.
        """
        print("Настройка: Полный сценарий с двумя tool_calls и их результатами...")
        request = ChatCompletionRequest(
            model="claude-sonnet-4-5",
            messages=[
                ChatMessage(role="user", content="Run two commands"),
                # Первый assistant с tool_call
                ChatMessage(
                    role="assistant",
                    content=None,
                    tool_calls=[{
                        "id": "tooluse_first",
                        "type": "function",
                        "function": {
                            "name": "shell",
                            "arguments": '{"command": ["ls"]}'
                        }
                    }]
                ),
                # Второй assistant с tool_call (подряд!)
                ChatMessage(
                    role="assistant",
                    content=None,
                    tool_calls=[{
                        "id": "tooluse_second",
                        "type": "function",
                        "function": {
                            "name": "shell",
                            "arguments": '{"command": ["pwd"]}'
                        }
                    }]
                ),
                # Результаты обоих tool_calls
                ChatMessage(role="tool", content="file1.txt\nfile2.txt", tool_call_id="tooluse_first"),
                ChatMessage(role="tool", content="/home/user", tool_call_id="tooluse_second")
            ]
        )
        
        print("Действие: Построение Kiro payload...")
        result = build_kiro_payload(request, "conv-123", "arn:aws:test")
        
        print(f"Результат: {result}")
        
        # Проверяем историю
        history = result["conversationState"].get("history", [])
        print(f"История: {history}")
        
        # Должен быть userInputMessage и assistantResponseMessage в истории
        assert len(history) >= 2, f"Ожидалось минимум 2 элемента в истории, получено {len(history)}"
        
        # Находим assistantResponseMessage
        assistant_msgs = [h for h in history if "assistantResponseMessage" in h]
        print(f"Assistant сообщения в истории: {assistant_msgs}")
        assert len(assistant_msgs) >= 1, "Должен быть хотя бы один assistantResponseMessage"
        
        # Проверяем, что в assistantResponseMessage есть оба toolUses
        assistant_msg = assistant_msgs[0]["assistantResponseMessage"]
        tool_uses = assistant_msg.get("toolUses", [])
        print(f"ToolUses в assistant: {tool_uses}")
        print(f"Сравниваем количество toolUses: Ожидалось 2, Получено {len(tool_uses)}")
        assert len(tool_uses) == 2, f"Должно быть 2 toolUses, получено {len(tool_uses)}"
        
        tool_use_ids = [tu["toolUseId"] for tu in tool_uses]
        print(f"ToolUse IDs: {tool_use_ids}")
        assert "tooluse_first" in tool_use_ids
        assert "tooluse_second" in tool_use_ids
        
        # Проверяем currentMessage содержит toolResults
        current_msg = result["conversationState"]["currentMessage"]["userInputMessage"]
        context = current_msg.get("userInputMessageContext", {})
        tool_results = context.get("toolResults", [])
        print(f"ToolResults в currentMessage: {tool_results}")
        print(f"Сравниваем количество toolResults: Ожидалось 2, Получено {len(tool_results)}")
        assert len(tool_results) == 2, f"Должно быть 2 toolResults, получено {len(tool_results)}"
        
        tool_result_ids = [tr["toolUseId"] for tr in tool_results]
        print(f"ToolResult IDs: {tool_result_ids}")
        assert "tooluse_first" in tool_result_ids
        assert "tooluse_second" in tool_result_ids


class TestBuildKiroPayload:
    """Тесты функции build_kiro_payload."""
    
    def test_builds_simple_payload(self):
        """
        Что он делает: Проверяет построение простого payload.
        Цель: Убедиться, что базовый запрос преобразуется корректно.
        """
        print("Настройка: Простой запрос...")
        request = ChatCompletionRequest(
            model="claude-sonnet-4-5",
            messages=[ChatMessage(role="user", content="Hello")]
        )
        
        print("Действие: Построение payload...")
        result = build_kiro_payload(request, "conv-123", "arn:aws:test")
        
        print(f"Результат: {result}")
        assert "conversationState" in result
        assert result["conversationState"]["conversationId"] == "conv-123"
        assert "currentMessage" in result["conversationState"]
        assert result["profileArn"] == "arn:aws:test"
    
    def test_includes_system_prompt_in_first_message(self):
        """
        Что он делает: Проверяет добавление system prompt к первому сообщению.
        Цель: Убедиться, что system prompt объединяется с user сообщением.
        """
        print("Настройка: Запрос с system prompt...")
        request = ChatCompletionRequest(
            model="claude-sonnet-4-5",
            messages=[
                ChatMessage(role="system", content="You are helpful"),
                ChatMessage(role="user", content="Hello")
            ]
        )
        
        print("Действие: Построение payload...")
        result = build_kiro_payload(request, "conv-123", "")
        
        print(f"Результат: {result}")
        current_content = result["conversationState"]["currentMessage"]["userInputMessage"]["content"]
        assert "You are helpful" in current_content
        assert "Hello" in current_content
    
    def test_builds_history_for_multi_turn(self):
        """
        Что он делает: Проверяет построение истории для multi-turn.
        Цель: Убедиться, что предыдущие сообщения попадают в history.
        """
        print("Настройка: Multi-turn запрос...")
        request = ChatCompletionRequest(
            model="claude-sonnet-4-5",
            messages=[
                ChatMessage(role="user", content="Hello"),
                ChatMessage(role="assistant", content="Hi"),
                ChatMessage(role="user", content="How are you?")
            ]
        )
        
        print("Действие: Построение payload...")
        result = build_kiro_payload(request, "conv-123", "")
        
        print(f"Результат: {result}")
        assert "history" in result["conversationState"]
        assert len(result["conversationState"]["history"]) == 2
    
    def test_handles_assistant_as_last_message(self):
        """
        Что он делает: Проверяет обработку assistant как последнего сообщения.
        Цель: Убедиться, что создаётся "Continue" сообщение.
        """
        print("Настройка: Запрос с assistant в конце...")
        request = ChatCompletionRequest(
            model="claude-sonnet-4-5",
            messages=[
                ChatMessage(role="user", content="Hello"),
                ChatMessage(role="assistant", content="Hi there")
            ]
        )
        
        print("Действие: Построение payload...")
        result = build_kiro_payload(request, "conv-123", "")
        
        print(f"Результат: {result}")
        current_content = result["conversationState"]["currentMessage"]["userInputMessage"]["content"]
        assert current_content == "Continue"
    
    def test_raises_for_empty_messages(self):
        """
        Что он делает: Проверяет выброс исключения для пустых сообщений.
        Цель: Убедиться, что пустой запрос вызывает ValueError.
        """
        print("Настройка: Запрос только с system сообщением...")
        request = ChatCompletionRequest(
            model="claude-sonnet-4-5",
            messages=[ChatMessage(role="system", content="You are helpful")]
        )
        
        print("Действие: Попытка построения payload...")
        with pytest.raises(ValueError) as exc_info:
            build_kiro_payload(request, "conv-123", "")
        
        print(f"Исключение: {exc_info.value}")
        assert "No messages to send" in str(exc_info.value)
    
    def test_uses_continue_for_empty_content(self):
        """
        Что он делает: Проверяет использование "Continue" для пустого контента.
        Цель: Убедиться, что пустое сообщение заменяется на "Continue".
        """
        print("Настройка: Запрос с пустым контентом...")
        request = ChatCompletionRequest(
            model="claude-sonnet-4-5",
            messages=[ChatMessage(role="user", content="")]
        )
        
        print("Действие: Построение payload...")
        result = build_kiro_payload(request, "conv-123", "")
        
        print(f"Результат: {result}")
        current_content = result["conversationState"]["currentMessage"]["userInputMessage"]["content"]
        assert current_content == "Continue"
    
    def test_maps_model_id_correctly(self):
        """
        Что он делает: Проверяет маппинг внешнего ID модели во внутренний.
        Цель: Убедиться, что MODEL_MAPPING применяется.
        """
        print("Настройка: Запрос с внешним ID модели...")
        request = ChatCompletionRequest(
            model="claude-sonnet-4-5",
            messages=[ChatMessage(role="user", content="Hello")]
        )
        
        print("Действие: Построение payload...")
        result = build_kiro_payload(request, "conv-123", "")
        
        print(f"Результат: {result}")
        model_id = result["conversationState"]["currentMessage"]["userInputMessage"]["modelId"]
        # claude-sonnet-4-5 должен маппиться в CLAUDE_SONNET_4_5_20250929_V1_0
        assert model_id == "CLAUDE_SONNET_4_5_20250929_V1_0"
    
    def test_long_tool_description_added_to_system_prompt(self):
        """
        Что он делает: Проверяет интеграцию длинных tool descriptions в payload.
        Цель: Убедиться, что длинные descriptions добавляются в system prompt в payload.
        """
        print("Настройка: Запрос с tool с длинным description...")
        long_desc = "X" * 15000
        request = ChatCompletionRequest(
            model="claude-sonnet-4-5",
            messages=[
                ChatMessage(role="system", content="You are helpful"),
                ChatMessage(role="user", content="Hello")
            ],
            tools=[Tool(
                type="function",
                function=ToolFunction(
                    name="long_tool",
                    description=long_desc,
                    parameters={}
                )
            )]
        )
        
        print("Действие: Построение payload...")
        with patch('kiro_gateway.converters.TOOL_DESCRIPTION_MAX_LENGTH', 10000):
            result = build_kiro_payload(request, "conv-123", "")
        
        print(f"Проверяем, что system prompt содержит tool documentation...")
        current_content = result["conversationState"]["currentMessage"]["userInputMessage"]["content"]
        assert "You are helpful" in current_content
        assert "## Tool: long_tool" in current_content
        assert long_desc in current_content
        
        print(f"Проверяем, что tool в context имеет reference description...")
        tools_context = result["conversationState"]["currentMessage"]["userInputMessage"]["userInputMessageContext"]["tools"]
        assert "[Full documentation in system prompt" in tools_context[0]["toolSpecification"]["description"]