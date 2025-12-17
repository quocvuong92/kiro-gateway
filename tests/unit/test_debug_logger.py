# -*- coding: utf-8 -*-

"""
Unit-тесты для DebugLogger.
Проверяет логику буферизации и записи debug логов в разных режимах.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestDebugLoggerModeOff:
    """Тесты для режима DEBUG_MODE=off."""
    
    def test_prepare_new_request_does_nothing(self, tmp_path):
        """
        Что он делает: Проверяет, что prepare_new_request ничего не делает в режиме off.
        Цель: Убедиться, что в режиме off директория не создаётся.
        """
        print("Настройка: Режим off...")
        with patch('kiro_gateway.debug_logger.DEBUG_MODE', 'off'):
            with patch('kiro_gateway.debug_logger.DEBUG_DIR', str(tmp_path / "debug_logs")):
                # Пересоздаём экземпляр с новыми настройками
                from kiro_gateway.debug_logger import DebugLogger
                logger = DebugLogger.__new__(DebugLogger)
                logger._initialized = False
                logger.__init__()
                logger.debug_dir = tmp_path / "debug_logs"
                
                print("Действие: Вызов prepare_new_request...")
                logger.prepare_new_request()
                
                print(f"Проверяем, что директория не создана...")
                assert not (tmp_path / "debug_logs").exists()
    
    def test_log_request_body_does_nothing(self, tmp_path):
        """
        Что он делает: Проверяет, что log_request_body ничего не делает в режиме off.
        Цель: Убедиться, что данные не записываются.
        """
        print("Настройка: Режим off...")
        with patch('kiro_gateway.debug_logger.DEBUG_MODE', 'off'):
            from kiro_gateway.debug_logger import DebugLogger
            logger = DebugLogger.__new__(DebugLogger)
            logger._initialized = False
            logger.__init__()
            logger.debug_dir = tmp_path / "debug_logs"
            
            print("Действие: Вызов log_request_body...")
            logger.log_request_body(b'{"test": "data"}')
            
            print(f"Проверяем, что файл не создан...")
            assert not (tmp_path / "debug_logs" / "request_body.json").exists()


class TestDebugLoggerModeAll:
    """Тесты для режима DEBUG_MODE=all."""
    
    def test_prepare_new_request_clears_directory(self, tmp_path):
        """
        Что он делает: Проверяет, что prepare_new_request очищает директорию в режиме all.
        Цель: Убедиться, что старые логи удаляются.
        """
        print("Настройка: Режим all, создаём старый файл...")
        debug_dir = tmp_path / "debug_logs"
        debug_dir.mkdir()
        old_file = debug_dir / "old_file.txt"
        old_file.write_text("old content")
        
        with patch('kiro_gateway.debug_logger.DEBUG_MODE', 'all'):
            from kiro_gateway.debug_logger import DebugLogger
            logger = DebugLogger.__new__(DebugLogger)
            logger._initialized = False
            logger.__init__()
            logger.debug_dir = debug_dir
            
            print("Действие: Вызов prepare_new_request...")
            logger.prepare_new_request()
            
            print(f"Проверяем, что старый файл удалён...")
            assert not old_file.exists()
            print(f"Проверяем, что директория существует...")
            assert debug_dir.exists()
    
    def test_log_request_body_writes_immediately(self, tmp_path):
        """
        Что он делает: Проверяет, что log_request_body пишет сразу в файл в режиме all.
        Цель: Убедиться, что данные записываются немедленно.
        """
        print("Настройка: Режим all...")
        debug_dir = tmp_path / "debug_logs"
        debug_dir.mkdir()
        
        with patch('kiro_gateway.debug_logger.DEBUG_MODE', 'all'):
            from kiro_gateway.debug_logger import DebugLogger
            logger = DebugLogger.__new__(DebugLogger)
            logger._initialized = False
            logger.__init__()
            logger.debug_dir = debug_dir
            
            print("Действие: Вызов log_request_body...")
            test_data = b'{"model": "test", "messages": []}'
            logger.log_request_body(test_data)
            
            print(f"Проверяем, что файл создан...")
            file_path = debug_dir / "request_body.json"
            assert file_path.exists()
            
            print(f"Проверяем содержимое файла...")
            content = json.loads(file_path.read_text())
            assert content["model"] == "test"
    
    def test_log_kiro_request_body_writes_immediately(self, tmp_path):
        """
        Что он делает: Проверяет, что log_kiro_request_body пишет сразу в файл в режиме all.
        Цель: Убедиться, что Kiro payload записывается немедленно.
        """
        print("Настройка: Режим all...")
        debug_dir = tmp_path / "debug_logs"
        debug_dir.mkdir()
        
        with patch('kiro_gateway.debug_logger.DEBUG_MODE', 'all'):
            from kiro_gateway.debug_logger import DebugLogger
            logger = DebugLogger.__new__(DebugLogger)
            logger._initialized = False
            logger.__init__()
            logger.debug_dir = debug_dir
            
            print("Действие: Вызов log_kiro_request_body...")
            test_data = b'{"conversationState": {}}'
            logger.log_kiro_request_body(test_data)
            
            print(f"Проверяем, что файл создан...")
            file_path = debug_dir / "kiro_request_body.json"
            assert file_path.exists()
    
    def test_log_raw_chunk_appends_to_file(self, tmp_path):
        """
        Что он делает: Проверяет, что log_raw_chunk дописывает в файл в режиме all.
        Цель: Убедиться, что чанки накапливаются.
        """
        print("Настройка: Режим all...")
        debug_dir = tmp_path / "debug_logs"
        debug_dir.mkdir()
        
        with patch('kiro_gateway.debug_logger.DEBUG_MODE', 'all'):
            from kiro_gateway.debug_logger import DebugLogger
            logger = DebugLogger.__new__(DebugLogger)
            logger._initialized = False
            logger.__init__()
            logger.debug_dir = debug_dir
            
            print("Действие: Вызов log_raw_chunk дважды...")
            logger.log_raw_chunk(b'chunk1')
            logger.log_raw_chunk(b'chunk2')
            
            print(f"Проверяем содержимое файла...")
            file_path = debug_dir / "response_stream_raw.txt"
            content = file_path.read_bytes()
            assert content == b'chunk1chunk2'


class TestDebugLoggerModeErrors:
    """Тесты для режима DEBUG_MODE=errors."""
    
    def test_log_request_body_buffers_data(self, tmp_path):
        """
        Что он делает: Проверяет, что log_request_body буферизует данные в режиме errors.
        Цель: Убедиться, что данные не записываются сразу.
        """
        print("Настройка: Режим errors...")
        debug_dir = tmp_path / "debug_logs"
        
        with patch('kiro_gateway.debug_logger.DEBUG_MODE', 'errors'):
            from kiro_gateway.debug_logger import DebugLogger
            logger = DebugLogger.__new__(DebugLogger)
            logger._initialized = False
            logger.__init__()
            logger.debug_dir = debug_dir
            
            print("Действие: Вызов log_request_body...")
            test_data = b'{"test": "buffered"}'
            logger.log_request_body(test_data)
            
            print(f"Проверяем, что файл НЕ создан...")
            assert not debug_dir.exists()
            
            print(f"Проверяем, что данные в буфере...")
            assert logger._request_body_buffer == test_data
    
    def test_flush_on_error_writes_buffers(self, tmp_path):
        """
        Что он делает: Проверяет, что flush_on_error записывает буферы в файлы.
        Цель: Убедиться, что при ошибке данные сохраняются.
        """
        print("Настройка: Режим errors, заполняем буферы...")
        debug_dir = tmp_path / "debug_logs"
        
        with patch('kiro_gateway.debug_logger.DEBUG_MODE', 'errors'):
            from kiro_gateway.debug_logger import DebugLogger
            logger = DebugLogger.__new__(DebugLogger)
            logger._initialized = False
            logger.__init__()
            logger.debug_dir = debug_dir
            
            # Заполняем буферы
            logger.log_request_body(b'{"request": "body"}')
            logger.log_kiro_request_body(b'{"kiro": "request"}')
            logger.log_raw_chunk(b'raw_chunk')
            logger.log_modified_chunk(b'modified_chunk')
            
            print("Действие: Вызов flush_on_error...")
            logger.flush_on_error(400, "Bad Request")
            
            print(f"Проверяем, что все файлы созданы...")
            assert (debug_dir / "request_body.json").exists()
            assert (debug_dir / "kiro_request_body.json").exists()
            assert (debug_dir / "response_stream_raw.txt").exists()
            assert (debug_dir / "response_stream_modified.txt").exists()
            assert (debug_dir / "error_info.json").exists()
            
            print(f"Проверяем error_info.json...")
            error_info = json.loads((debug_dir / "error_info.json").read_text())
            assert error_info["status_code"] == 400
            assert error_info["error_message"] == "Bad Request"
    
    def test_flush_on_error_clears_buffers(self, tmp_path):
        """
        Что он делает: Проверяет, что flush_on_error очищает буферы после записи.
        Цель: Убедиться, что буферы не накапливаются между запросами.
        """
        print("Настройка: Режим errors...")
        debug_dir = tmp_path / "debug_logs"
        
        with patch('kiro_gateway.debug_logger.DEBUG_MODE', 'errors'):
            from kiro_gateway.debug_logger import DebugLogger
            logger = DebugLogger.__new__(DebugLogger)
            logger._initialized = False
            logger.__init__()
            logger.debug_dir = debug_dir
            
            logger.log_request_body(b'{"test": "data"}')
            
            print("Действие: Вызов flush_on_error...")
            logger.flush_on_error(500, "Error")
            
            print(f"Проверяем, что буферы очищены...")
            assert logger._request_body_buffer is None
            assert logger._kiro_request_body_buffer is None
            assert len(logger._raw_chunks_buffer) == 0
            assert len(logger._modified_chunks_buffer) == 0
    
    def test_discard_buffers_clears_without_writing(self, tmp_path):
        """
        Что он делает: Проверяет, что discard_buffers очищает буферы без записи.
        Цель: Убедиться, что успешные запросы не оставляют логов.
        """
        print("Настройка: Режим errors, заполняем буферы...")
        debug_dir = tmp_path / "debug_logs"
        
        with patch('kiro_gateway.debug_logger.DEBUG_MODE', 'errors'):
            from kiro_gateway.debug_logger import DebugLogger
            logger = DebugLogger.__new__(DebugLogger)
            logger._initialized = False
            logger.__init__()
            logger.debug_dir = debug_dir
            
            logger.log_request_body(b'{"test": "data"}')
            logger.log_raw_chunk(b'chunk')
            
            print("Действие: Вызов discard_buffers...")
            logger.discard_buffers()
            
            print(f"Проверяем, что директория НЕ создана...")
            assert not debug_dir.exists()
            
            print(f"Проверяем, что буферы очищены...")
            assert logger._request_body_buffer is None
            assert len(logger._raw_chunks_buffer) == 0
    
    def test_flush_on_error_writes_error_info_in_mode_all(self, tmp_path):
        """
        Что он делает: Проверяет, что flush_on_error записывает error_info.json в режиме all.
        Цель: Убедиться, что информация об ошибке сохраняется в обоих режимах.
        """
        print("Настройка: Режим all...")
        debug_dir = tmp_path / "debug_logs"
        
        with patch('kiro_gateway.debug_logger.DEBUG_MODE', 'all'):
            from kiro_gateway.debug_logger import DebugLogger
            logger = DebugLogger.__new__(DebugLogger)
            logger._initialized = False
            logger.__init__()
            logger.debug_dir = debug_dir
            
            print("Действие: Вызов flush_on_error...")
            logger.flush_on_error(400, "Bad Request")
            
            print(f"Проверяем, что error_info.json создан...")
            assert (debug_dir / "error_info.json").exists()
            
            print(f"Проверяем содержимое error_info.json...")
            error_info = json.loads((debug_dir / "error_info.json").read_text())
            assert error_info["status_code"] == 400
            assert error_info["error_message"] == "Bad Request"


class TestDebugLoggerLogErrorInfo:
    """Тесты для метода log_error_info()."""
    
    def test_log_error_info_writes_in_mode_all(self, tmp_path):
        """
        Что он делает: Проверяет, что log_error_info записывает файл в режиме all.
        Цель: Убедиться, что error_info.json создаётся при ошибках.
        """
        print("Настройка: Режим all...")
        debug_dir = tmp_path / "debug_logs"
        
        with patch('kiro_gateway.debug_logger.DEBUG_MODE', 'all'):
            from kiro_gateway.debug_logger import DebugLogger
            logger = DebugLogger.__new__(DebugLogger)
            logger._initialized = False
            logger.__init__()
            logger.debug_dir = debug_dir
            
            print("Действие: Вызов log_error_info...")
            logger.log_error_info(500, "Internal Server Error")
            
            print(f"Проверяем, что error_info.json создан...")
            error_file = debug_dir / "error_info.json"
            assert error_file.exists()
            
            print(f"Проверяем содержимое...")
            error_info = json.loads(error_file.read_text())
            assert error_info["status_code"] == 500
            assert error_info["error_message"] == "Internal Server Error"
    
    def test_log_error_info_writes_in_mode_errors(self, tmp_path):
        """
        Что он делает: Проверяет, что log_error_info записывает файл в режиме errors.
        Цель: Убедиться, что метод работает в обоих режимах.
        """
        print("Настройка: Режим errors...")
        debug_dir = tmp_path / "debug_logs"
        
        with patch('kiro_gateway.debug_logger.DEBUG_MODE', 'errors'):
            from kiro_gateway.debug_logger import DebugLogger
            logger = DebugLogger.__new__(DebugLogger)
            logger._initialized = False
            logger.__init__()
            logger.debug_dir = debug_dir
            
            print("Действие: Вызов log_error_info...")
            logger.log_error_info(404, "Not Found")
            
            print(f"Проверяем, что error_info.json создан...")
            error_file = debug_dir / "error_info.json"
            assert error_file.exists()
    
    def test_log_error_info_does_nothing_in_mode_off(self, tmp_path):
        """
        Что он делает: Проверяет, что log_error_info ничего не делает в режиме off.
        Цель: Убедиться, что в режиме off файлы не создаются.
        """
        print("Настройка: Режим off...")
        debug_dir = tmp_path / "debug_logs"
        
        with patch('kiro_gateway.debug_logger.DEBUG_MODE', 'off'):
            from kiro_gateway.debug_logger import DebugLogger
            logger = DebugLogger.__new__(DebugLogger)
            logger._initialized = False
            logger.__init__()
            logger.debug_dir = debug_dir
            
            print("Действие: Вызов log_error_info...")
            logger.log_error_info(500, "Error")
            
            print(f"Проверяем, что директория НЕ создана...")
            assert not debug_dir.exists()


class TestDebugLoggerHelperMethods:
    """Тесты для вспомогательных методов DebugLogger."""
    
    def test_is_enabled_returns_true_for_errors(self):
        """
        Что он делает: Проверяет _is_enabled() для режима errors.
        Цель: Убедиться, что режим errors считается включённым.
        """
        print("Настройка: Режим errors...")
        with patch('kiro_gateway.debug_logger.DEBUG_MODE', 'errors'):
            from kiro_gateway.debug_logger import DebugLogger
            logger = DebugLogger.__new__(DebugLogger)
            logger._initialized = False
            logger.__init__()
            
            print(f"Проверяем _is_enabled()...")
            assert logger._is_enabled() is True
    
    def test_is_enabled_returns_true_for_all(self):
        """
        Что он делает: Проверяет _is_enabled() для режима all.
        Цель: Убедиться, что режим all считается включённым.
        """
        print("Настройка: Режим all...")
        with patch('kiro_gateway.debug_logger.DEBUG_MODE', 'all'):
            from kiro_gateway.debug_logger import DebugLogger
            logger = DebugLogger.__new__(DebugLogger)
            logger._initialized = False
            logger.__init__()
            
            print(f"Проверяем _is_enabled()...")
            assert logger._is_enabled() is True
    
    def test_is_enabled_returns_false_for_off(self):
        """
        Что он делает: Проверяет _is_enabled() для режима off.
        Цель: Убедиться, что режим off считается выключенным.
        """
        print("Настройка: Режим off...")
        with patch('kiro_gateway.debug_logger.DEBUG_MODE', 'off'):
            from kiro_gateway.debug_logger import DebugLogger
            logger = DebugLogger.__new__(DebugLogger)
            logger._initialized = False
            logger.__init__()
            
            print(f"Проверяем _is_enabled()...")
            assert logger._is_enabled() is False
    
    def test_is_immediate_write_returns_true_for_all(self):
        """
        Что он делает: Проверяет _is_immediate_write() для режима all.
        Цель: Убедиться, что режим all пишет сразу.
        """
        print("Настройка: Режим all...")
        with patch('kiro_gateway.debug_logger.DEBUG_MODE', 'all'):
            from kiro_gateway.debug_logger import DebugLogger
            logger = DebugLogger.__new__(DebugLogger)
            logger._initialized = False
            logger.__init__()
            
            print(f"Проверяем _is_immediate_write()...")
            assert logger._is_immediate_write() is True
    
    def test_is_immediate_write_returns_false_for_errors(self):
        """
        Что он делает: Проверяет _is_immediate_write() для режима errors.
        Цель: Убедиться, что режим errors буферизует.
        """
        print("Настройка: Режим errors...")
        with patch('kiro_gateway.debug_logger.DEBUG_MODE', 'errors'):
            from kiro_gateway.debug_logger import DebugLogger
            logger = DebugLogger.__new__(DebugLogger)
            logger._initialized = False
            logger.__init__()
            
            print(f"Проверяем _is_immediate_write()...")
            assert logger._is_immediate_write() is False


class TestDebugLoggerJsonHandling:
    """Тесты для обработки JSON в DebugLogger."""
    
    def test_log_request_body_formats_json_pretty(self, tmp_path):
        """
        Что он делает: Проверяет, что JSON форматируется красиво.
        Цель: Убедиться, что JSON читаем в файле.
        """
        print("Настройка: Режим all...")
        debug_dir = tmp_path / "debug_logs"
        debug_dir.mkdir()
        
        with patch('kiro_gateway.debug_logger.DEBUG_MODE', 'all'):
            from kiro_gateway.debug_logger import DebugLogger
            logger = DebugLogger.__new__(DebugLogger)
            logger._initialized = False
            logger.__init__()
            logger.debug_dir = debug_dir
            
            print("Действие: Вызов log_request_body с JSON...")
            logger.log_request_body(b'{"key":"value"}')
            
            print(f"Проверяем форматирование...")
            content = (debug_dir / "request_body.json").read_text()
            # Должен быть отформатирован с отступами
            assert "  " in content or "\n" in content
    
    def test_log_request_body_handles_invalid_json(self, tmp_path):
        """
        Что он делает: Проверяет обработку невалидного JSON.
        Цель: Убедиться, что невалидный JSON записывается как есть.
        """
        print("Настройка: Режим all...")
        debug_dir = tmp_path / "debug_logs"
        debug_dir.mkdir()
        
        with patch('kiro_gateway.debug_logger.DEBUG_MODE', 'all'):
            from kiro_gateway.debug_logger import DebugLogger
            logger = DebugLogger.__new__(DebugLogger)
            logger._initialized = False
            logger.__init__()
            logger.debug_dir = debug_dir
            
            print("Действие: Вызов log_request_body с невалидным JSON...")
            invalid_data = b'not a json {{'
            logger.log_request_body(invalid_data)
            
            print(f"Проверяем, что данные записаны как есть...")
            content = (debug_dir / "request_body.json").read_bytes()
            assert content == invalid_data