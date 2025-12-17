# Тесты для Kiro OpenAI Gateway

Комплексный набор unit и integration тестов для Kiro OpenAI Gateway, обеспечивающий полное покрытие всех компонентов системы.

## Философия тестирования: Полная изоляция от сети

**Ключевой принцип этого тестового набора — 100% изоляция от реальных сетевых запросов.**

Это достигается с помощью глобальной, автоматически применяемой фикстуры `block_all_network_calls` в `tests/conftest.py`. Она перехватывает и блокирует любые попытки `httpx.AsyncClient` установить соединение на уровне всего приложения.

**Преимущества:**
1.  **Надежность**: Тесты не зависят от доступности внешних API и состояния сети.
2.  **Скорость**: Отсутствие реальных сетевых задержек делает выполнение тестов мгновенным.
3.  **Безопасность**: Гарантирует, что тестовые запуски никогда не используют реальные учетные данные.

Любая попытка совершить несанкционированный сетевой вызов приведет к немедленному падению теста с ошибкой, что обеспечивает строгий контроль над изоляцией.

## Запуск тестов

### Установка зависимостей

```bash
# Основные зависимости проекта
pip install -r requirements.txt

# Дополнительные зависимости для тестирования
pip install pytest pytest-asyncio hypothesis
```

### Запуск всех тестов

```bash
# Запуск всего набора тестов
pytest

# Запуск с подробным выводом
pytest -v

# Запуск с подробным выводом и покрытием
pytest -v -s --tb=short

# Запуск только unit-тестов
pytest tests/unit/ -v

# Запуск только integration-тестов
pytest tests/integration/ -v

# Запуск конкретного файла
pytest tests/unit/test_auth_manager.py -v

# Запуск конкретного теста
pytest tests/unit/test_auth_manager.py::TestKiroAuthManagerInitialization::test_initialization_stores_credentials -v
```

### Опции pytest

```bash
# Остановка на первой ошибке
pytest -x

# Показать локальные переменные при ошибках
pytest -l

# Запуск в параллельном режиме (требует pytest-xdist)
pip install pytest-xdist
pytest -n auto
```

## Структура тестов

```
tests/
├── conftest.py                      # Общие фикстуры и утилиты
├── unit/                            # Unit-тесты отдельных компонентов
│   ├── test_auth_manager.py        # Тесты KiroAuthManager
│   ├── test_cache.py               # Тесты ModelInfoCache
│   ├── test_config.py              # Тесты конфигурации (LOG_LEVEL и др.)
│   ├── test_converters.py          # Тесты конвертеров OpenAI <-> Kiro
│   ├── test_debug_logger.py        # Тесты DebugLogger (режимы off/errors/all)
│   ├── test_parsers.py             # Тесты AwsEventStreamParser
│   ├── test_streaming.py           # Тесты streaming функций
│   ├── test_tokenizer.py           # Тесты токенизатора (tiktoken)
│   ├── test_http_client.py         # Тесты KiroHttpClient
│   └── test_routes.py              # Тесты API endpoints
├── integration/                     # Integration-тесты полного flow
│   └── test_full_flow.py           # End-to-end тесты
└── README.md                        # Этот файл
```

## Покрытие тестами

### `conftest.py`

Общие фикстуры и утилиты для всех тестов:

**Фикстуры окружения:**
- **`mock_env_vars()`**: Мокирует переменные окружения (REFRESH_TOKEN, PROXY_API_KEY)
  - **Что он делает**: Изолирует тесты от реальных credentials
  - **Цель**: Безопасность и воспроизводимость тестов

**Фикстуры данных:**
- **`valid_kiro_token()`**: Возвращает мок Kiro access token
  - **Что он делает**: Предоставляет предсказуемый токен для тестов
  - **Цель**: Тестирование без реальных запросов к Kiro

- **`mock_kiro_token_response()`**: Фабрика для создания мок ответов refreshToken
  - **Что он делает**: Генерирует структуру ответа Kiro auth endpoint
  - **Цель**: Тестирование различных сценариев обновления токена

- **`temp_creds_file()`**: Создаёт временный JSON файл с credentials
  - **Что он делает**: Предоставляет файл для тестирования загрузки credentials
  - **Цель**: Тестирование работы с файлами credentials

- **`sample_openai_chat_request()`**: Фабрика для создания OpenAI запросов
  - **Что он делает**: Генерирует валидные chat completion requests
  - **Цель**: Удобное создание тестовых запросов с разными параметрами

**Фикстуры безопасности:**
- **`valid_proxy_api_key()`**: Валидный API ключ прокси
- **`invalid_proxy_api_key()`**: Невалидный ключ для негативных тестов
- **`auth_headers()`**: Фабрика для создания Authorization заголовков

**Фикстуры HTTP:**
- **`mock_httpx_client()`**: Мокированный httpx.AsyncClient
  - **Что он делает**: Изолирует тесты от реальных HTTP запросов
  - **Цель**: Скорость и надежность тестов

- **`mock_httpx_response()`**: Фабрика для создания мок HTTP responses
  - **Что он делает**: Создает настраиваемые httpx.Response объекты
  - **Цель**: Тестирование различных HTTP сценариев

**Фикстуры приложения:**
- **`clean_app()`**: Чистый экземпляр FastAPI app
  - **Что он делает**: Возвращает "чистый" экземпляр приложения
  - **Цель**: Обеспечить изоляцию состояния приложения между тестами

- **`test_client()`**: Синхронный FastAPI TestClient
- **`async_test_client()`**: Асинхронный test client для async endpoints

---

### `tests/unit/test_auth_manager.py`

Unit-тесты для **KiroAuthManager** (управление токенами Kiro).

#### `TestKiroAuthManagerInitialization`

- **`test_initialization_stores_credentials()`**:
  - **Что он делает**: Проверяет корректное сохранение credentials при создании
  - **Цель**: Убедиться, что все параметры конструктора сохраняются в приватных полях

- **`test_initialization_sets_correct_urls_for_region()`**:
  - **Что он делает**: Проверяет формирование URL на основе региона
  - **Цель**: Убедиться, что URL динамически формируются с правильным регионом

- **`test_initialization_generates_fingerprint()`**:
  - **Что он делает**: Проверяет генерацию уникального fingerprint
  - **Цель**: Убедиться, что fingerprint генерируется и имеет корректный формат

#### `TestKiroAuthManagerCredentialsFile`

- **`test_load_credentials_from_file()`**:
  - **Что он делает**: Проверяет загрузку credentials из JSON файла
  - **Цель**: Убедиться, что данные корректно читаются из файла

- **`test_load_credentials_file_not_found()`**:
  - **Что он делает**: Проверяет обработку отсутствующего файла credentials
  - **Цель**: Убедиться, что приложение не падает при отсутствии файла

#### `TestKiroAuthManagerTokenExpiration`

- **`test_is_token_expiring_soon_returns_true_when_no_expires_at()`**:
  - **Что он делает**: Проверяет, что без expires_at токен считается истекающим
  - **Цель**: Убедиться в безопасном поведении при отсутствии информации о времени

- **`test_is_token_expiring_soon_returns_true_when_expired()`**:
  - **Что он делает**: Проверяет, что истекший токен определяется корректно
  - **Цель**: Убедиться, что токен в прошлом считается истекающим

- **`test_is_token_expiring_soon_returns_true_within_threshold()`**:
  - **Что он делает**: Проверяет, что токен в пределах threshold считается истекающим
  - **Цель**: Убедиться, что токен обновляется заранее (за 10 минут до истечения)

- **`test_is_token_expiring_soon_returns_false_when_valid()`**:
  - **Что он делает**: Проверяет, что валидный токен не считается истекающим
  - **Цель**: Убедиться, что токен далеко в будущем не требует обновления

#### `TestKiroAuthManagerTokenRefresh`

- **`test_refresh_token_successful()`**:
  - **Что он делает**: Тестирует успешное обновление токена через Kiro API
  - **Цель**: Проверить корректную установку access_token и expires_at

- **`test_refresh_token_updates_refresh_token()`**:
  - **Что он делает**: Проверяет обновление refresh_token из ответа
  - **Цель**: Убедиться, что новый refresh_token сохраняется

- **`test_refresh_token_missing_access_token_raises()`**:
  - **Что он делает**: Проверяет обработку ответа без accessToken
  - **Цель**: Убедиться, что выбрасывается исключение при некорректном ответе

- **`test_refresh_token_no_refresh_token_raises()`**:
  - **Что он делает**: Проверяет обработку отсутствия refresh_token
  - **Цель**: Убедиться, что выбрасывается исключение без refresh_token

#### `TestKiroAuthManagerGetAccessToken`

- **`test_get_access_token_refreshes_when_expired()`**:
  - **Что он делает**: Проверяет автоматическое обновление истекшего токена
  - **Цель**: Убедиться, что устаревший токен обновляется перед возвратом

- **`test_get_access_token_returns_valid_without_refresh()`**:
  - **Что он делает**: Проверяет возврат валидного токена без лишних запросов
  - **Цель**: Оптимизация - не делать запросы, если токен еще действителен

- **`test_get_access_token_thread_safety()`**:
  - **Что он делает**: Проверяет потокобезопасность через asyncio.Lock
  - **Цель**: Предотвращение race conditions при параллельных вызовах

#### `TestKiroAuthManagerForceRefresh`

- **`test_force_refresh_updates_token()`**:
  - **Что он делает**: Проверяет принудительное обновление токена
  - **Цель**: Убедиться, что force_refresh всегда обновляет токен

#### `TestKiroAuthManagerProperties`

- **`test_profile_arn_property()`**:
  - **Что он делает**: Проверяет свойство profile_arn
  - **Цель**: Убедиться, что profile_arn доступен через property

- **`test_region_property()`**:
  - **Что он делает**: Проверяет свойство region
  - **Цель**: Убедиться, что region доступен через property

- **`test_api_host_property()`**:
  - **Что он делает**: Проверяет свойство api_host
  - **Цель**: Убедиться, что api_host формируется корректно

- **`test_fingerprint_property()`**:
  - **Что он делает**: Проверяет свойство fingerprint
  - **Цель**: Убедиться, что fingerprint доступен через property

---

### `tests/unit/test_cache.py`

Unit-тесты для **ModelInfoCache** (кэш метаданных моделей). **23 теста.**

#### `TestModelInfoCacheInitialization`

- **`test_initialization_creates_empty_cache()`**:
  - **Что он делает**: Проверяет, что кэш создаётся пустым
  - **Цель**: Убедиться в корректной инициализации

- **`test_initialization_with_custom_ttl()`**:
  - **Что он делает**: Проверяет создание кэша с кастомным TTL
  - **Цель**: Убедиться, что TTL можно настроить

- **`test_initialization_last_update_is_none()`**:
  - **Что он делает**: Проверяет, что last_update_time изначально None
  - **Цель**: Убедиться, что время обновления не установлено до первого update

#### `TestModelInfoCacheUpdate`

- **`test_update_populates_cache()`**:
  - **Что он делает**: Проверяет заполнение кэша данными
  - **Цель**: Убедиться, что update() корректно сохраняет модели

- **`test_update_sets_last_update_time()`**:
  - **Что он делает**: Проверяет установку времени последнего обновления
  - **Цель**: Убедиться, что last_update_time устанавливается после update

- **`test_update_replaces_existing_data()`**:
  - **Что он делает**: Проверяет замену данных при повторном update
  - **Цель**: Убедиться, что старые данные полностью заменяются

- **`test_update_with_empty_list()`**:
  - **Что он делает**: Проверяет обновление пустым списком
  - **Цель**: Убедиться, что кэш очищается при пустом update

#### `TestModelInfoCacheGet`

- **`test_get_returns_model_info()`**:
  - **Что он делает**: Проверяет получение информации о модели
  - **Цель**: Убедиться, что get() возвращает корректные данные

- **`test_get_returns_none_for_unknown_model()`**:
  - **Что он делает**: Проверяет возврат None для неизвестной модели
  - **Цель**: Убедиться, что get() не падает при отсутствии модели

- **`test_get_from_empty_cache()`**:
  - **Что он делает**: Проверяет get() из пустого кэша
  - **Цель**: Убедиться, что пустой кэш не вызывает ошибок

#### `TestModelInfoCacheGetMaxInputTokens`

- **`test_get_max_input_tokens_returns_value()`**:
  - **Что он делает**: Проверяет получение maxInputTokens для модели
  - **Цель**: Убедиться, что значение извлекается из tokenLimits

- **`test_get_max_input_tokens_returns_default_for_unknown()`**:
  - **Что он делает**: Проверяет возврат дефолта для неизвестной модели
  - **Цель**: Убедиться, что возвращается DEFAULT_MAX_INPUT_TOKENS

- **`test_get_max_input_tokens_returns_default_when_no_token_limits()`**:
  - **Что он делает**: Проверяет возврат дефолта при отсутствии tokenLimits
  - **Цель**: Убедиться, что модель без tokenLimits не ломает логику

- **`test_get_max_input_tokens_returns_default_when_max_input_is_none()`**:
  - **Что он делает**: Проверяет возврат дефолта при maxInputTokens=None
  - **Цель**: Убедиться, что None в tokenLimits обрабатывается корректно

#### `TestModelInfoCacheIsEmpty` и `TestModelInfoCacheIsStale`

- **`test_is_empty_returns_true_for_new_cache()`**: Проверяет is_empty() для нового кэша
- **`test_is_empty_returns_false_after_update()`**: Проверяет is_empty() после заполнения
- **`test_is_stale_returns_true_for_new_cache()`**: Проверяет is_stale() для нового кэша
- **`test_is_stale_returns_false_after_recent_update()`**: Проверяет is_stale() сразу после обновления
- **`test_is_stale_returns_true_after_ttl_expires()`**: Проверяет is_stale() после истечения TTL

#### `TestModelInfoCacheGetAllModelIds`

- **`test_get_all_model_ids_returns_empty_for_new_cache()`**: Проверяет get_all_model_ids() для пустого кэша
- **`test_get_all_model_ids_returns_all_ids()`**: Проверяет get_all_model_ids() для заполненного кэша

#### `TestModelInfoCacheThreadSafety`

- **`test_concurrent_updates_dont_corrupt_cache()`**:
  - **Что он делает**: Проверяет потокобезопасность при параллельных update
  - **Цель**: Убедиться, что asyncio.Lock защищает от race conditions

- **`test_concurrent_reads_are_safe()`**:
  - **Что он делает**: Проверяет безопасность параллельных чтений
  - **Цель**: Убедиться, что множественные get() не вызывают проблем

---

### `tests/unit/test_config.py`

Unit-тесты для **модуля конфигурации** (загрузка настроек из переменных окружения). **9 тестов.**

#### `TestLogLevelConfig`

Тесты для настройки LOG_LEVEL.

- **`test_default_log_level_is_info()`**:
  - **Что он делает**: Проверяет, что LOG_LEVEL по умолчанию равен INFO
  - **Цель**: Убедиться, что без переменной окружения используется INFO

- **`test_log_level_from_environment()`**:
  - **Что он делает**: Проверяет загрузку LOG_LEVEL из переменной окружения
  - **Цель**: Убедиться, что значение из окружения используется

- **`test_log_level_uppercase_conversion()`**:
  - **Что он делает**: Проверяет преобразование LOG_LEVEL в верхний регистр
  - **Цель**: Убедиться, что lowercase значение преобразуется в uppercase

- **`test_log_level_trace()`**:
  - **Что он делает**: Проверяет установку LOG_LEVEL=TRACE
  - **Цель**: Убедиться, что TRACE уровень поддерживается

- **`test_log_level_error()`**:
  - **Что он делает**: Проверяет установку LOG_LEVEL=ERROR
  - **Цель**: Убедиться, что ERROR уровень поддерживается

- **`test_log_level_critical()`**:
  - **Что он делает**: Проверяет установку LOG_LEVEL=CRITICAL
  - **Цель**: Убедиться, что CRITICAL уровень поддерживается

#### `TestToolDescriptionMaxLengthConfig`

Тесты для настройки TOOL_DESCRIPTION_MAX_LENGTH.

- **`test_default_tool_description_max_length()`**:
  - **Что он делает**: Проверяет значение по умолчанию для TOOL_DESCRIPTION_MAX_LENGTH
  - **Цель**: Убедиться, что по умолчанию используется 10000

- **`test_tool_description_max_length_from_environment()`**:
  - **Что он делает**: Проверяет загрузку TOOL_DESCRIPTION_MAX_LENGTH из окружения
  - **Цель**: Убедиться, что значение из окружения используется

- **`test_tool_description_max_length_zero_disables()`**:
  - **Что он делает**: Проверяет, что 0 отключает функцию
  - **Цель**: Убедиться, что TOOL_DESCRIPTION_MAX_LENGTH=0 работает

---

### `tests/unit/test_debug_logger.py`

Unit-тесты для **DebugLogger** (отладочное логирование запросов). **26 тестов.**

#### `TestDebugLoggerModeOff`

Тесты для режима DEBUG_MODE=off.

- **`test_prepare_new_request_does_nothing()`**:
  - **Что он делает**: Проверяет, что prepare_new_request ничего не делает в режиме off
  - **Цель**: Убедиться, что в режиме off директория не создаётся

- **`test_log_request_body_does_nothing()`**:
  - **Что он делает**: Проверяет, что log_request_body ничего не делает в режиме off
  - **Цель**: Убедиться, что данные не записываются

#### `TestDebugLoggerModeAll`

Тесты для режима DEBUG_MODE=all.

- **`test_prepare_new_request_clears_directory()`**:
  - **Что он делает**: Проверяет, что prepare_new_request очищает директорию в режиме all
  - **Цель**: Убедиться, что старые логи удаляются

- **`test_log_request_body_writes_immediately()`**:
  - **Что он делает**: Проверяет, что log_request_body пишет сразу в файл в режиме all
  - **Цель**: Убедиться, что данные записываются немедленно

- **`test_log_kiro_request_body_writes_immediately()`**:
  - **Что он делает**: Проверяет, что log_kiro_request_body пишет сразу в файл в режиме all
  - **Цель**: Убедиться, что Kiro payload записывается немедленно

- **`test_log_raw_chunk_appends_to_file()`**:
  - **Что он делает**: Проверяет, что log_raw_chunk дописывает в файл в режиме all
  - **Цель**: Убедиться, что чанки накапливаются

#### `TestDebugLoggerModeErrors`

Тесты для режима DEBUG_MODE=errors.

- **`test_log_request_body_buffers_data()`**:
  - **Что он делает**: Проверяет, что log_request_body буферизует данные в режиме errors
  - **Цель**: Убедиться, что данные не записываются сразу

- **`test_flush_on_error_writes_buffers()`**:
  - **Что он делает**: Проверяет, что flush_on_error записывает буферы в файлы
  - **Цель**: Убедиться, что при ошибке данные сохраняются

- **`test_flush_on_error_clears_buffers()`**:
  - **Что он делает**: Проверяет, что flush_on_error очищает буферы после записи
  - **Цель**: Убедиться, что буферы не накапливаются между запросами

- **`test_discard_buffers_clears_without_writing()`**:
  - **Что он делает**: Проверяет, что discard_buffers очищает буферы без записи
  - **Цель**: Убедиться, что успешные запросы не оставляют логов

- **`test_flush_on_error_writes_error_info_in_mode_all()`**:
  - **Что он делает**: Проверяет, что flush_on_error записывает error_info.json в режиме all
  - **Цель**: Убедиться, что информация об ошибке сохраняется в обоих режимах

#### `TestDebugLoggerLogErrorInfo`

Тесты для метода log_error_info().

- **`test_log_error_info_writes_in_mode_all()`**:
  - **Что он делает**: Проверяет, что log_error_info записывает файл в режиме all
  - **Цель**: Убедиться, что error_info.json создаётся при ошибках

- **`test_log_error_info_writes_in_mode_errors()`**:
  - **Что он делает**: Проверяет, что log_error_info записывает файл в режиме errors
  - **Цель**: Убедиться, что метод работает в обоих режимах

- **`test_log_error_info_does_nothing_in_mode_off()`**:
  - **Что он делает**: Проверяет, что log_error_info ничего не делает в режиме off
  - **Цель**: Убедиться, что в режиме off файлы не создаются

#### `TestDebugLoggerHelperMethods`

Тесты для вспомогательных методов DebugLogger.

- **`test_is_enabled_returns_true_for_errors()`**: Проверяет _is_enabled() для режима errors
- **`test_is_enabled_returns_true_for_all()`**: Проверяет _is_enabled() для режима all
- **`test_is_enabled_returns_false_for_off()`**: Проверяет _is_enabled() для режима off
- **`test_is_immediate_write_returns_true_for_all()`**: Проверяет _is_immediate_write() для режима all
- **`test_is_immediate_write_returns_false_for_errors()`**: Проверяет _is_immediate_write() для режима errors

#### `TestDebugLoggerJsonHandling`

Тесты для обработки JSON в DebugLogger.

- **`test_log_request_body_formats_json_pretty()`**:
  - **Что он делает**: Проверяет, что JSON форматируется красиво
  - **Цель**: Убедиться, что JSON читаем в файле

- **`test_log_request_body_handles_invalid_json()`**:
  - **Что он делает**: Проверяет обработку невалидного JSON
  - **Цель**: Убедиться, что невалидный JSON записывается как есть

#### `TestDebugLoggerAppLogsCapture`

Тесты для захвата логов приложения (app_logs.txt).

- **`test_prepare_new_request_sets_up_log_capture()`**:
  - **Что он делает**: Проверяет, что prepare_new_request настраивает захват логов
  - **Цель**: Убедиться, что sink для логов создаётся

- **`test_flush_on_error_writes_app_logs_in_mode_errors()`**:
  - **Что он делает**: Проверяет, что flush_on_error записывает app_logs.txt в режиме errors
  - **Цель**: Убедиться, что логи приложения сохраняются при ошибках

- **`test_discard_buffers_saves_logs_in_mode_all()`**:
  - **Что он делает**: Проверяет, что discard_buffers сохраняет логи в режиме all
  - **Цель**: Убедиться, что даже успешные запросы сохраняют логи в режиме all

- **`test_discard_buffers_does_not_save_logs_in_mode_errors()`**:
  - **Что он делает**: Проверяет, что discard_buffers НЕ сохраняет логи в режиме errors
  - **Цель**: Убедиться, что успешные запросы не оставляют логов в режиме errors

- **`test_clear_app_logs_buffer_removes_sink()`**:
  - **Что он делает**: Проверяет, что _clear_app_logs_buffer удаляет sink
  - **Цель**: Убедиться, что sink корректно удаляется

- **`test_app_logs_not_saved_when_empty()`**:
  - **Что он делает**: Проверяет, что пустые логи не создают файл
  - **Цель**: Убедиться, что app_logs.txt не создаётся если логов нет

---

### `tests/unit/test_converters.py`

Unit-тесты для конвертеров **OpenAI <-> Kiro**. **68 тестов.**

#### `TestExtractTextContent`

- **`test_extracts_from_string()`**: Проверяет извлечение текста из строки
- **`test_extracts_from_none()`**: Проверяет обработку None
- **`test_extracts_from_list_with_text_type()`**: Проверяет извлечение из списка с type=text
- **`test_extracts_from_list_with_text_key()`**: Проверяет извлечение из списка с ключом text
- **`test_extracts_from_list_with_strings()`**: Проверяет извлечение из списка строк
- **`test_extracts_from_mixed_list()`**: Проверяет извлечение из смешанного списка
- **`test_converts_other_types_to_string()`**: Проверяет конвертацию других типов в строку
- **`test_handles_empty_list()`**: Проверяет обработку пустого списка

#### `TestMergeAdjacentMessages`

- **`test_merges_adjacent_user_messages()`**: Проверяет объединение соседних user сообщений
- **`test_preserves_alternating_messages()`**: Проверяет сохранение чередующихся сообщений
- **`test_handles_empty_list()`**: Проверяет обработку пустого списка
- **`test_handles_single_message()`**: Проверяет обработку одного сообщения
- **`test_merges_multiple_adjacent_groups()`**: Проверяет объединение нескольких групп

**Новые тесты для обработки tool messages (role="tool"):**

- **`test_converts_tool_message_to_user_with_tool_result()`**:
  - **Что он делает**: Проверяет преобразование tool message в user message с tool_result
  - **Цель**: Убедиться, что role="tool" преобразуется в user message с tool_results content

- **`test_converts_multiple_tool_messages_to_single_user_message()`**:
  - **Что он делает**: Проверяет объединение нескольких tool messages в один user message
  - **Цель**: Убедиться, что несколько tool results объединяются в один user message

- **`test_tool_message_followed_by_user_message()`**:
  - **Что он делает**: Проверяет tool message перед user message
  - **Цель**: Убедиться, что tool results и user message объединяются

- **`test_assistant_tool_user_sequence()`**:
  - **Что он делает**: Проверяет последовательность assistant -> tool -> user
  - **Цель**: Убедиться, что tool message корректно вставляется между assistant и user

- **`test_tool_message_with_empty_content()`**:
  - **Что он делает**: Проверяет tool message с пустым content
  - **Цель**: Убедиться, что пустой результат заменяется на "(empty result)"

- **`test_tool_message_with_none_tool_call_id()`**:
  - **Что он делает**: Проверяет tool message без tool_call_id
  - **Цель**: Убедиться, что отсутствующий tool_call_id заменяется на пустую строку

- **`test_merges_list_contents_correctly()`**:
  - **Что он делает**: Проверяет объединение list contents
  - **Цель**: Убедиться, что списки объединяются корректно

- **`test_merges_adjacent_assistant_tool_calls()`**:
  - **Что он делает**: Проверяет объединение tool_calls при merge соседних assistant сообщений
  - **Цель**: Убедиться, что tool_calls из всех assistant сообщений сохраняются при объединении

- **`test_merges_three_adjacent_assistant_tool_calls()`**:
  - **Что он делает**: Проверяет объединение tool_calls из трёх assistant сообщений
  - **Цель**: Убедиться, что все tool_calls сохраняются при объединении более двух сообщений

- **`test_merges_assistant_with_and_without_tool_calls()`**:
  - **Что он делает**: Проверяет объединение assistant с tool_calls и без
  - **Цель**: Убедиться, что tool_calls корректно инициализируются при объединении

#### `TestBuildKiroPayloadToolCallsIntegration`

Интеграционные тесты для полного flow tool_calls от OpenAI до Kiro формата.

- **`test_multiple_assistant_tool_calls_with_results()`**:
  - **Что он делает**: Проверяет полный сценарий с несколькими assistant tool_calls и их результатами
  - **Цель**: Убедиться, что все toolUses и toolResults корректно связываются в Kiro payload

#### `TestBuildKiroHistory`

- **`test_builds_user_message()`**: Проверяет построение user сообщения
- **`test_builds_assistant_message()`**: Проверяет построение assistant сообщения
- **`test_ignores_system_messages()`**: Проверяет игнорирование system сообщений
- **`test_builds_conversation_history()`**: Проверяет построение полной истории разговора
- **`test_handles_empty_list()`**: Проверяет обработку пустого списка

#### `TestExtractToolResults` и `TestExtractToolUses`

- **`test_extracts_tool_results_from_list()`**: Проверяет извлечение tool results из списка
- **`test_returns_empty_for_string_content()`**: Проверяет возврат пустого списка для строки
- **`test_extracts_from_tool_calls_field()`**: Проверяет извлечение из поля tool_calls
- **`test_extracts_from_content_list()`**: Проверяет извлечение из content списка

#### `TestProcessToolsWithLongDescriptions`

Тесты для функции обработки tools с длинными descriptions (Tool Documentation Reference Pattern).

- **`test_returns_none_and_empty_string_for_none_tools()`**:
  - **Что он делает**: Проверяет обработку None вместо списка tools
  - **Цель**: Убедиться, что None возвращает (None, "")

- **`test_returns_none_and_empty_string_for_empty_list()`**:
  - **Что он делает**: Проверяет обработку пустого списка tools
  - **Цель**: Убедиться, что пустой список возвращает (None, "")

- **`test_short_description_unchanged()`**:
  - **Что он делает**: Проверяет, что короткие descriptions не изменяются
  - **Цель**: Убедиться, что tools с короткими descriptions остаются как есть

- **`test_long_description_moved_to_system_prompt()`**:
  - **Что он делает**: Проверяет перенос длинного description в system prompt
  - **Цель**: Убедиться, что длинные descriptions переносятся корректно с reference в tool

- **`test_mixed_short_and_long_descriptions()`**:
  - **Что он делает**: Проверяет обработку смешанного списка tools
  - **Цель**: Убедиться, что короткие остаются, длинные переносятся

- **`test_preserves_tool_parameters()`**:
  - **Что он делает**: Проверяет сохранение parameters при переносе description
  - **Цель**: Убедиться, что parameters не теряются

- **`test_disabled_when_limit_is_zero()`**:
  - **Что он делает**: Проверяет отключение функции при лимите 0
  - **Цель**: Убедиться, что при TOOL_DESCRIPTION_MAX_LENGTH=0 tools не изменяются

- **`test_non_function_tools_unchanged()`**:
  - **Что он делает**: Проверяет, что non-function tools не изменяются
  - **Цель**: Убедиться, что только function tools обрабатываются

- **`test_multiple_long_descriptions_all_moved()`**:
  - **Что он делает**: Проверяет перенос нескольких длинных descriptions
  - **Цель**: Убедиться, что все длинные descriptions переносятся

- **`test_empty_description_unchanged()`**:
  - **Что он делает**: Проверяет обработку пустого description
  - **Цель**: Убедиться, что пустой description не вызывает ошибок

- **`test_none_description_unchanged()`**:
  - **Что он делает**: Проверяет обработку None description
  - **Цель**: Убедиться, что None description не вызывает ошибок

#### `TestSanitizeJsonSchema`

Тесты для функции `_sanitize_json_schema`, которая очищает JSON Schema от полей, не поддерживаемых Kiro API.

- **`test_returns_empty_dict_for_none()`**:
  - **Что он делает**: Проверяет обработку None
  - **Цель**: Убедиться, что None возвращает пустой словарь

- **`test_returns_empty_dict_for_empty_dict()`**:
  - **Что он делает**: Проверяет обработку пустого словаря
  - **Цель**: Убедиться, что пустой словарь возвращается как есть

- **`test_removes_empty_required_array()`**:
  - **Что он делает**: Проверяет удаление пустого required массива
  - **Цель**: Убедиться, что `required: []` удаляется из schema (критический тест для бага Cline)

- **`test_preserves_non_empty_required_array()`**:
  - **Что он делает**: Проверяет сохранение непустого required массива
  - **Цель**: Убедиться, что required с элементами сохраняется

- **`test_removes_additional_properties()`**:
  - **Что он делает**: Проверяет удаление additionalProperties
  - **Цель**: Убедиться, что additionalProperties удаляется из schema

- **`test_removes_both_empty_required_and_additional_properties()`**:
  - **Что он делает**: Проверяет удаление обоих проблемных полей
  - **Цель**: Убедиться, что оба поля удаляются одновременно (реальный сценарий от Cline)

- **`test_recursively_sanitizes_nested_properties()`**:
  - **Что он делает**: Проверяет рекурсивную очистку вложенных properties
  - **Цель**: Убедиться, что вложенные schema также очищаются

- **`test_recursively_sanitizes_dict_values()`**:
  - **Что он делает**: Проверяет рекурсивную очистку dict значений
  - **Цель**: Убедиться, что любые вложенные dict очищаются

- **`test_sanitizes_items_in_lists()`**:
  - **Что он делает**: Проверяет очистку элементов в списках (anyOf, oneOf)
  - **Цель**: Убедиться, что элементы списков также очищаются

- **`test_preserves_non_dict_list_items()`**:
  - **Что он делает**: Проверяет сохранение не-dict элементов в списках
  - **Цель**: Убедиться, что строки и другие типы в списках сохраняются

- **`test_complex_real_world_schema()`**:
  - **Что он делает**: Проверяет очистку реальной сложной schema от Cline
  - **Цель**: Убедиться, что реальные schema обрабатываются корректно

#### `TestBuildUserInputContext`

- **`test_builds_tools_context()`**: Проверяет построение контекста с tools
- **`test_returns_empty_for_no_tools()`**: Проверяет возврат пустого контекста без tools

**Новые тесты для placeholder пустых descriptions (исправление бага Cline):**

- **`test_empty_description_replaced_with_placeholder()`**:
  - **Что он делает**: Проверяет замену пустого description на placeholder
  - **Цель**: Убедиться, что пустой description заменяется на "Tool: {name}" (критический тест для бага Cline с focus_chain)

- **`test_whitespace_only_description_replaced_with_placeholder()`**:
  - **Что он делает**: Проверяет замену description из пробелов на placeholder
  - **Цель**: Убедиться, что description с только пробелами заменяется

- **`test_none_description_replaced_with_placeholder()`**:
  - **Что он делает**: Проверяет замену None description на placeholder
  - **Цель**: Убедиться, что None description заменяется на "Tool: {name}"

- **`test_non_empty_description_preserved()`**:
  - **Что он делает**: Проверяет сохранение непустого description
  - **Цель**: Убедиться, что нормальный description не изменяется

- **`test_sanitizes_tool_parameters()`**:
  - **Что он делает**: Проверяет очистку parameters от проблемных полей
  - **Цель**: Убедиться, что _sanitize_json_schema применяется к parameters

- **`test_mixed_tools_with_empty_and_normal_descriptions()`**:
  - **Что он делает**: Проверяет обработку смешанного списка tools
  - **Цель**: Убедиться, что пустые descriptions заменяются, а нормальные сохраняются (реальный сценарий от Cline)

#### `TestBuildKiroPayload`

- **`test_builds_simple_payload()`**: Проверяет построение простого payload
- **`test_includes_system_prompt_in_first_message()`**: Проверяет добавление system prompt
- **`test_builds_history_for_multi_turn()`**: Проверяет построение истории для multi-turn
- **`test_handles_assistant_as_last_message()`**: Проверяет обработку assistant как последнего сообщения
- **`test_raises_for_empty_messages()`**: Проверяет выброс исключения для пустых сообщений
- **`test_uses_continue_for_empty_content()`**: Проверяет использование "Continue" для пустого контента
- **`test_maps_model_id_correctly()`**: Проверяет маппинг внешнего ID модели во внутренний
- **`test_long_tool_description_added_to_system_prompt()`**:
  - **Что он делает**: Проверяет интеграцию длинных tool descriptions в payload
  - **Цель**: Убедиться, что длинные descriptions добавляются в system prompt в payload

---

### `tests/unit/test_parsers.py`

Unit-тесты для **AwsEventStreamParser** и вспомогательных функций парсинга. **52 теста.**

#### `TestFindMatchingBrace`

- **`test_simple_json_object()`**: Проверяет поиск закрывающей скобки для простого JSON
- **`test_nested_json_object()`**: Проверяет поиск для вложенного JSON
- **`test_json_with_braces_in_string()`**: Проверяет игнорирование скобок внутри строк
- **`test_json_with_escaped_quotes()`**: Проверяет обработку экранированных кавычек
- **`test_incomplete_json()`**: Проверяет обработку незавершённого JSON
- **`test_invalid_start_position()`**: Проверяет обработку невалидной стартовой позиции
- **`test_start_position_out_of_bounds()`**: Проверяет обработку позиции за пределами текста

#### `TestParseBracketToolCalls`

- **`test_parses_single_tool_call()`**: Проверяет парсинг одного tool call
- **`test_parses_multiple_tool_calls()`**: Проверяет парсинг нескольких tool calls
- **`test_returns_empty_for_no_tool_calls()`**: Проверяет возврат пустого списка без tool calls
- **`test_returns_empty_for_empty_string()`**: Проверяет обработку пустой строки
- **`test_returns_empty_for_none()`**: Проверяет обработку None
- **`test_handles_nested_json_in_args()`**: Проверяет парсинг вложенного JSON в аргументах
- **`test_generates_unique_ids()`**: Проверяет генерацию уникальных ID для tool calls

#### `TestDeduplicateToolCalls`

- **`test_removes_duplicates()`**: Проверяет удаление дубликатов
- **`test_preserves_first_occurrence()`**: Проверяет сохранение первого вхождения
- **`test_handles_empty_list()`**: Проверяет обработку пустого списка

**Новые тесты для улучшенной дедупликации по id:**

- **`test_deduplicates_by_id_keeps_one_with_arguments()`**:
  - **Что он делает**: Проверяет дедупликацию по id с сохранением tool call с аргументами
  - **Цель**: Убедиться, что при дубликатах по id сохраняется тот, у которого есть аргументы

- **`test_deduplicates_by_id_prefers_longer_arguments()`**:
  - **Что он делает**: Проверяет, что при дубликатах по id предпочитаются более длинные аргументы
  - **Цель**: Убедиться, что сохраняется tool call с более полными аргументами

- **`test_deduplicates_empty_arguments_replaced_by_non_empty()`**:
  - **Что он делает**: Проверяет замену пустых аргументов на непустые
  - **Цель**: Убедиться, что "{}" заменяется на реальные аргументы

- **`test_handles_tool_calls_without_id()`**:
  - **Что он делает**: Проверяет обработку tool calls без id
  - **Цель**: Убедиться, что tool calls без id дедуплицируются по name+arguments

- **`test_mixed_with_and_without_id()`**:
  - **Что он делает**: Проверяет смешанный список с id и без
  - **Цель**: Убедиться, что оба типа обрабатываются корректно

#### `TestAwsEventStreamParserInitialization`

- **`test_initialization_creates_empty_state()`**: Проверяет начальное состояние парсера

#### `TestAwsEventStreamParserFeed`

- **`test_parses_content_event()`**: Проверяет парсинг события с контентом
- **`test_parses_multiple_content_events()`**: Проверяет парсинг нескольких событий контента
- **`test_deduplicates_repeated_content()`**: Проверяет дедупликацию повторяющегося контента
- **`test_parses_usage_event()`**: Проверяет парсинг события usage
- **`test_parses_context_usage_event()`**: Проверяет парсинг события context_usage
- **`test_handles_incomplete_json()`**: Проверяет обработку неполного JSON
- **`test_completes_json_across_chunks()`**: Проверяет сборку JSON из нескольких chunks
- **`test_decodes_escape_sequences()`**: Проверяет декодирование escape-последовательностей
- **`test_handles_invalid_bytes()`**: Проверяет обработку невалидных байтов

#### `TestAwsEventStreamParserToolCalls`

- **`test_parses_tool_start_event()`**: Проверяет парсинг начала tool call
- **`test_parses_tool_input_event()`**: Проверяет парсинг input для tool call
- **`test_parses_tool_stop_event()`**: Проверяет завершение tool call
- **`test_get_tool_calls_returns_all()`**: Проверяет получение всех tool calls
- **`test_get_tool_calls_finalizes_current()`**: Проверяет завершение незавершённого tool call

#### `TestAwsEventStreamParserReset`

- **`test_reset_clears_state()`**: Проверяет сброс состояния парсера

#### `TestAwsEventStreamParserFinalizeToolCall`

**Новые тесты для метода _finalize_tool_call с разными типами input:**

- **`test_finalize_with_string_arguments()`**:
  - **Что он делает**: Проверяет финализацию tool call со строковыми аргументами
  - **Цель**: Убедиться, что строка JSON парсится и сериализуется обратно

- **`test_finalize_with_dict_arguments()`**:
  - **Что он делает**: Проверяет финализацию tool call с dict аргументами
  - **Цель**: Убедиться, что dict сериализуется в JSON строку

- **`test_finalize_with_empty_string_arguments()`**:
  - **Что он делает**: Проверяет финализацию tool call с пустой строкой аргументов
  - **Цель**: Убедиться, что пустая строка заменяется на "{}"

- **`test_finalize_with_whitespace_only_arguments()`**:
  - **Что он делает**: Проверяет финализацию tool call с пробельными аргументами
  - **Цель**: Убедиться, что строка из пробелов заменяется на "{}"

- **`test_finalize_with_invalid_json_arguments()`**:
  - **Что он делает**: Проверяет финализацию tool call с невалидным JSON
  - **Цель**: Убедиться, что невалидный JSON заменяется на "{}"

- **`test_finalize_with_none_current_tool_call()`**:
  - **Что он делает**: Проверяет финализацию когда current_tool_call is None
  - **Цель**: Убедиться, что ничего не происходит при None

- **`test_finalize_clears_current_tool_call()`**:
  - **Что он делает**: Проверяет, что финализация очищает current_tool_call
  - **Цель**: Убедиться, что после финализации current_tool_call = None

#### `TestAwsEventStreamParserEdgeCases`

- **`test_handles_followup_prompt()`**: Проверяет игнорирование followupPrompt
- **`test_handles_mixed_events()`**: Проверяет парсинг смешанных событий
- **`test_handles_garbage_between_events()`**: Проверяет обработку мусора между событиями
- **`test_handles_empty_chunk()`**: Проверяет обработку пустого chunk

---

### `tests/unit/test_tokenizer.py`

Unit-тесты для **модуля токенизатора** (подсчёт токенов с помощью tiktoken). **32 теста.**

#### `TestCountTokens`

Тесты для функции count_tokens.

- **`test_empty_string_returns_zero()`**:
  - **Что он делает**: Проверяет, что пустая строка возвращает 0 токенов
  - **Цель**: Убедиться в корректной обработке граничного случая

- **`test_none_returns_zero()`**:
  - **Что он делает**: Проверяет, что None возвращает 0 токенов
  - **Цель**: Убедиться в корректной обработке None

- **`test_simple_text_returns_positive()`**:
  - **Что он делает**: Проверяет, что простой текст возвращает положительное число токенов
  - **Цель**: Убедиться в базовой работоспособности подсчёта

- **`test_longer_text_returns_more_tokens()`**:
  - **Что он делает**: Проверяет, что более длинный текст возвращает больше токенов
  - **Цель**: Убедиться в корректной пропорциональности подсчёта

- **`test_claude_correction_applied_by_default()`**:
  - **Что он делает**: Проверяет, что коэффициент коррекции Claude применяется по умолчанию
  - **Цель**: Убедиться, что apply_claude_correction=True по умолчанию

- **`test_without_claude_correction()`**:
  - **Что он делает**: Проверяет подсчёт без коэффициента коррекции
  - **Цель**: Убедиться, что apply_claude_correction=False работает

- **`test_unicode_text()`**:
  - **Что он делает**: Проверяет подсчёт токенов для Unicode текста
  - **Цель**: Убедиться в корректной обработке не-ASCII символов

- **`test_multiline_text()`**:
  - **Что он делает**: Проверяет подсчёт токенов для многострочного текста
  - **Цель**: Убедиться в корректной обработке переносов строк

- **`test_json_text()`**:
  - **Что он делает**: Проверяет подсчёт токенов для JSON строки
  - **Цель**: Убедиться в корректной обработке JSON

#### `TestCountTokensFallback`

Тесты для fallback логики при отсутствии tiktoken.

- **`test_fallback_when_tiktoken_unavailable()`**:
  - **Что он делает**: Проверяет fallback подсчёт когда tiktoken недоступен
  - **Цель**: Убедиться, что система работает без tiktoken

- **`test_fallback_without_correction()`**:
  - **Что он делает**: Проверяет fallback без коэффициента коррекции
  - **Цель**: Убедиться, что fallback работает с apply_claude_correction=False

#### `TestCountMessageTokens`

Тесты для функции count_message_tokens.

- **`test_empty_list_returns_zero()`**:
  - **Что он делает**: Проверяет, что пустой список возвращает 0 токенов
  - **Цель**: Убедиться в корректной обработке пустого списка

- **`test_none_returns_zero()`**:
  - **Что он делает**: Проверяет, что None возвращает 0 токенов
  - **Цель**: Убедиться в корректной обработке None

- **`test_single_user_message()`**:
  - **Что он делает**: Проверяет подсчёт токенов для одного user сообщения
  - **Цель**: Убедиться в базовой работоспособности

- **`test_multiple_messages()`**:
  - **Что он делает**: Проверяет подсчёт токенов для нескольких сообщений
  - **Цель**: Убедиться, что токены суммируются корректно

- **`test_message_with_tool_calls()`**:
  - **Что он делает**: Проверяет подсчёт токенов для сообщения с tool_calls
  - **Цель**: Убедиться, что tool_calls учитываются

- **`test_message_with_tool_call_id()`**:
  - **Что он делает**: Проверяет подсчёт токенов для tool response сообщения
  - **Цель**: Убедиться, что tool_call_id учитывается

- **`test_message_with_list_content()`**:
  - **Что он делает**: Проверяет подсчёт токенов для мультимодального контента
  - **Цель**: Убедиться, что list content обрабатывается

- **`test_without_claude_correction()`**:
  - **Что он делает**: Проверяет подсчёт без коэффициента коррекции
  - **Цель**: Убедиться, что apply_claude_correction=False работает

- **`test_message_with_empty_content()`**:
  - **Что он делает**: Проверяет подсчёт для сообщения с пустым content
  - **Цель**: Убедиться, что пустой content не ломает подсчёт

- **`test_message_with_none_content()`**:
  - **Что он делает**: Проверяет подсчёт для сообщения с None content
  - **Цель**: Убедиться, что None content не ломает подсчёт

#### `TestCountToolsTokens`

Тесты для функции count_tools_tokens.

- **`test_none_returns_zero()`**:
  - **Что он делает**: Проверяет, что None возвращает 0 токенов
  - **Цель**: Убедиться в корректной обработке None

- **`test_empty_list_returns_zero()`**:
  - **Что он делает**: Проверяет, что пустой список возвращает 0 токенов
  - **Цель**: Убедиться в корректной обработке пустого списка

- **`test_single_tool()`**:
  - **Что он делает**: Проверяет подсчёт токенов для одного инструмента
  - **Цель**: Убедиться в базовой работоспособности

- **`test_multiple_tools()`**:
  - **Что он делает**: Проверяет подсчёт токенов для нескольких инструментов
  - **Цель**: Убедиться, что токены суммируются

- **`test_tool_with_complex_parameters()`**:
  - **Что он делает**: Проверяет подсчёт для инструмента со сложными параметрами
  - **Цель**: Убедиться, что JSON schema параметров учитывается

- **`test_tool_without_parameters()`**:
  - **Что он делает**: Проверяет подсчёт для инструмента без параметров
  - **Цель**: Убедиться, что отсутствие parameters не ломает подсчёт

- **`test_tool_with_empty_description()`**:
  - **Что он делает**: Проверяет подсчёт для инструмента с пустым description
  - **Цель**: Убедиться, что пустой description не ломает подсчёт

- **`test_non_function_tool_type()`**:
  - **Что он делает**: Проверяет обработку инструмента с type != "function"
  - **Цель**: Убедиться, что non-function tools обрабатываются

- **`test_without_claude_correction()`**:
  - **Что он делает**: Проверяет подсчёт без коэффициента коррекции
  - **Цель**: Убедиться, что apply_claude_correction=False работает

#### `TestEstimateRequestTokens`

Тесты для функции estimate_request_tokens.

- **`test_messages_only()`**:
  - **Что он делает**: Проверяет оценку токенов только для сообщений
  - **Цель**: Убедиться в базовой работоспособности

- **`test_messages_with_tools()`**:
  - **Что он делает**: Проверяет оценку токенов для сообщений с инструментами
  - **Цель**: Убедиться, что tools учитываются

- **`test_messages_with_system_prompt()`**:
  - **Что он делает**: Проверяет оценку токенов с отдельным system prompt
  - **Цель**: Убедиться, что system_prompt учитывается

- **`test_full_request()`**:
  - **Что он делает**: Проверяет оценку токенов для полного запроса
  - **Цель**: Убедиться, что все компоненты суммируются

- **`test_empty_messages()`**:
  - **Что он делает**: Проверяет оценку для пустого списка сообщений
  - **Цель**: Убедиться в корректной обработке граничного случая

#### `TestClaudeCorrectionFactor`

Тесты для коэффициента коррекции Claude.

- **`test_correction_factor_value()`**:
  - **Что он делает**: Проверяет значение коэффициента коррекции
  - **Цель**: Убедиться, что коэффициент равен 1.15

- **`test_correction_increases_token_count()`**:
  - **Что он делает**: Проверяет, что коррекция увеличивает количество токенов
  - **Цель**: Убедиться, что коэффициент применяется корректно

#### `TestGetEncoding`

Тесты для функции _get_encoding.

- **`test_returns_encoding_when_tiktoken_available()`**:
  - **Что он делает**: Проверяет, что _get_encoding возвращает encoding когда tiktoken доступен
  - **Цель**: Убедиться в корректной инициализации tiktoken

- **`test_caches_encoding()`**:
  - **Что он делает**: Проверяет, что encoding кэшируется
  - **Цель**: Убедиться в ленивой инициализации

- **`test_handles_import_error()`**:
  - **Что он делает**: Проверяет обработку ImportError при отсутствии tiktoken
  - **Цель**: Убедиться, что система работает без tiktoken

#### `TestTokenizerIntegration`

Интеграционные тесты для токенизатора.

- **`test_realistic_chat_request()`**:
  - **Что он делает**: Проверяет подсчёт токенов для реалистичного chat запроса
  - **Цель**: Убедиться в корректной работе на реальных данных

- **`test_large_context()`**:
  - **Что он делает**: Проверяет подсчёт токенов для большого контекста
  - **Цель**: Убедиться в производительности на больших данных

- **`test_consistency_across_calls()`**:
  - **Что он делает**: Проверяет консистентность подсчёта при повторных вызовах
  - **Цель**: Убедиться, что результаты детерминированы

---

### `tests/unit/test_streaming.py`

Unit-тесты для **streaming модуля** (преобразование потока Kiro в OpenAI формат). **8 тестов.**

#### `TestStreamingToolCallsIndex`

Тесты для добавления index к tool_calls в streaming ответах.

- **`test_tool_calls_have_index_field()`**:
  - **Что он делает**: Проверяет, что tool_calls в streaming ответе содержат поле index
  - **Цель**: Убедиться, что OpenAI API spec соблюдается для streaming tool calls

- **`test_multiple_tool_calls_have_sequential_indices()`**:
  - **Что он делает**: Проверяет, что несколько tool_calls имеют последовательные индексы
  - **Цель**: Убедиться, что индексы начинаются с 0 и идут последовательно

#### `TestStreamingToolCallsNoneProtection`

Тесты для защиты от None значений в tool_calls.

- **`test_handles_none_function_name()`**:
  - **Что он делает**: Проверяет обработку None в function.name
  - **Цель**: Убедиться, что None заменяется на пустую строку

- **`test_handles_none_function_arguments()`**:
  - **Что он делает**: Проверяет обработку None в function.arguments
  - **Цель**: Убедиться, что None заменяется на "{}"

- **`test_handles_none_function_object()`**:
  - **Что он делает**: Проверяет обработку None вместо function объекта
  - **Цель**: Убедиться, что None function обрабатывается без ошибок

#### `TestCollectStreamResponseToolCalls`

Тесты для collect_stream_response с tool_calls.

- **`test_collected_tool_calls_have_no_index()`**:
  - **Что он делает**: Проверяет, что собранные tool_calls не содержат поле index
  - **Цель**: Убедиться, что для non-streaming ответа index удаляется

- **`test_collected_tool_calls_have_required_fields()`**:
  - **Что он делает**: Проверяет, что собранные tool_calls содержат все обязательные поля
  - **Цель**: Убедиться, что id, type, function присутствуют

- **`test_handles_none_in_collected_tool_calls()`**:
  - **Что он делает**: Проверяет обработку None значений в собранных tool_calls
  - **Цель**: Убедиться, что None заменяются на дефолтные значения

---

### `tests/unit/test_http_client.py`

Unit-тесты для **KiroHttpClient** (HTTP клиент с retry логикой). **29 тестов.**

#### `TestKiroHttpClientInitialization`

- **`test_initialization_stores_auth_manager()`**: Проверяет сохранение auth_manager при инициализации
- **`test_initialization_client_is_none()`**: Проверяет, что HTTP клиент изначально None

#### `TestKiroHttpClientGetClient`

- **`test_get_client_creates_new_client()`**: Проверяет создание нового HTTP клиента
- **`test_get_client_reuses_existing_client()`**: Проверяет повторное использование существующего клиента
- **`test_get_client_recreates_closed_client()`**: Проверяет пересоздание закрытого клиента

#### `TestKiroHttpClientClose`

- **`test_close_closes_client()`**: Проверяет закрытие HTTP клиента
- **`test_close_does_nothing_for_none_client()`**: Проверяет, что close() не падает для None клиента
- **`test_close_does_nothing_for_closed_client()`**: Проверяет, что close() не падает для закрытого клиента

#### `TestKiroHttpClientRequestWithRetry`

- **`test_successful_request_returns_response()`**: Проверяет успешный запрос
- **`test_403_triggers_token_refresh()`**: Проверяет обновление токена при 403
- **`test_429_triggers_backoff()`**: Проверяет exponential backoff при 429
- **`test_5xx_triggers_backoff()`**: Проверяет exponential backoff при 5xx
- **`test_timeout_triggers_backoff()`**: Проверяет exponential backoff при таймауте
- **`test_request_error_triggers_backoff()`**: Проверяет exponential backoff при ошибке запроса
- **`test_max_retries_exceeded_raises_502()`**: Проверяет выброс HTTPException после исчерпания попыток
- **`test_other_status_codes_returned_as_is()`**: Проверяет возврат других статус-кодов без retry
- **`test_streaming_request_uses_send()`**: Проверяет использование send() для streaming

#### `TestKiroHttpClientContextManager`

- **`test_context_manager_returns_self()`**: Проверяет, что __aenter__ возвращает self
- **`test_context_manager_closes_on_exit()`**: Проверяет закрытие клиента при выходе из контекста

#### `TestKiroHttpClientExponentialBackoff`

- **`test_backoff_delay_increases_exponentially()`**: Проверяет экспоненциальное увеличение задержки

#### `TestKiroHttpClientFirstTokenTimeout`

**Новые тесты для логики first token timeout для streaming запросов:**

- **`test_streaming_uses_first_token_timeout()`**:
  - **Что он делает**: Проверяет, что streaming запросы используют FIRST_TOKEN_TIMEOUT
  - **Цель**: Убедиться, что для stream=True используется короткий таймаут

- **`test_streaming_uses_first_token_max_retries()`**:
  - **Что он делает**: Проверяет, что streaming запросы используют FIRST_TOKEN_MAX_RETRIES
  - **Цель**: Убедиться, что для stream=True используется отдельный счётчик retry

- **`test_streaming_timeout_retry_without_delay()`**:
  - **Что он делает**: Проверяет, что streaming таймаут retry происходит без задержки
  - **Цель**: Убедиться, что при first token timeout нет exponential backoff

- **`test_non_streaming_uses_default_timeout()`**:
  - **Что он делает**: Проверяет, что non-streaming запросы используют 300 секунд
  - **Цель**: Убедиться, что для stream=False используется длинный таймаут

- **`test_custom_first_token_timeout()`**:
  - **Что он делает**: Проверяет использование кастомного first_token_timeout
  - **Цель**: Убедиться, что параметр first_token_timeout переопределяет дефолт

- **`test_streaming_timeout_returns_504()`**:
  - **Что он делает**: Проверяет, что streaming таймаут возвращает 504
  - **Цель**: Убедиться, что после исчерпания попыток возвращается 504 Gateway Timeout

- **`test_non_streaming_timeout_returns_502()`**:
  - **Что он делает**: Проверяет, что non-streaming таймаут возвращает 502
  - **Цель**: Убедиться, что для non-streaming используется старая логика с 502

---

### `tests/unit/test_routes.py`

Unit-тесты для **API endpoints** (/v1/models, /v1/chat/completions). **22 теста.**

#### `TestVerifyApiKey`

- **`test_valid_api_key_returns_true()`**: Проверяет успешную валидацию корректного ключа
- **`test_invalid_api_key_raises_401()`**: Проверяет отклонение невалидного ключа
- **`test_missing_api_key_raises_401()`**: Проверяет отклонение отсутствующего ключа
- **`test_empty_api_key_raises_401()`**: Проверяет отклонение пустого ключа
- **`test_wrong_format_raises_401()`**: Проверяет отклонение ключа без Bearer

#### `TestRootEndpoint`

- **`test_root_returns_status_ok()`**: Проверяет ответ корневого эндпоинта
- **`test_root_returns_version()`**: Проверяет наличие версии в ответе

#### `TestHealthEndpoint`

- **`test_health_returns_healthy()`**: Проверяет ответ health эндпоинта
- **`test_health_returns_timestamp()`**: Проверяет наличие timestamp в ответе
- **`test_health_returns_version()`**: Проверяет наличие версии в ответе

#### `TestModelsEndpoint`

- **`test_models_requires_auth()`**: Проверяет требование авторизации
- **`test_models_returns_list()`**: Проверяет возврат списка моделей
- **`test_models_returns_available_models()`**: Проверяет наличие доступных моделей
- **`test_models_format_is_openai_compatible()`**: Проверяет формат ответа на совместимость с OpenAI

#### `TestChatCompletionsEndpoint`

- **`test_chat_completions_requires_auth()`**: Проверяет требование авторизации
- **`test_chat_completions_validates_messages()`**: Проверяет валидацию пустых сообщений
- **`test_chat_completions_validates_model()`**: Проверяет валидацию отсутствующей модели

#### `TestChatCompletionsWithMockedKiro`

- **`test_chat_completions_accepts_valid_request_format()`**: Проверяет, что валидный формат запроса принимается

#### `TestChatCompletionsErrorHandling`

- **`test_invalid_json_returns_422()`**: Проверяет обработку невалидного JSON
- **`test_missing_content_in_message_returns_200()`**: Проверяет обработку сообщения без content

#### `TestRouterIntegration`

- **`test_router_has_all_endpoints()`**: Проверяет наличие всех эндпоинтов в роутере
- **`test_router_methods()`**: Проверяет HTTP методы эндпоинтов

---

### `tests/integration/test_full_flow.py`

Integration-тесты для **полного end-to-end flow**. **12 тестов (11 passed, 1 skipped).**

#### `TestFullChatCompletionFlow`

- **`test_full_flow_health_to_models_to_chat()`**: Проверяет полный flow от health check до chat completions
- **`test_authentication_flow()`**: Проверяет flow аутентификации
- **`test_openai_compatibility_format()`**: Проверяет совместимость формата ответов с OpenAI API

#### `TestRequestValidationFlow`

- **`test_chat_completions_request_validation()`**: Проверяет валидацию различных форматов запросов
- **`test_complex_message_formats()`**: Проверяет обработку сложных форматов сообщений

#### `TestErrorHandlingFlow`

- **`test_invalid_json_handling()`**: Проверяет обработку невалидного JSON
- **`test_wrong_content_type_handling()`**: SKIPPED - обнаружен баг в validation_exception_handler

#### `TestModelsEndpointIntegration`

- **`test_models_returns_all_available_models()`**: Проверяет, что все модели из конфига возвращаются
- **`test_models_caching_behavior()`**: Проверяет поведение кэширования моделей

#### `TestStreamingFlagHandling`

- **`test_stream_true_accepted()`**: Проверяет, что stream=true принимается
- **`test_stream_false_accepted()`**: Проверяет, что stream=false принимается

#### `TestHealthEndpointIntegration`

- **`test_root_and_health_consistency()`**: Проверяет консистентность / и /health

---

## Философия тестирования

### Принципы

1. **Изоляция**: Каждый тест полностью изолирован от внешних сервисов через моки
2. **Детализация**: Обильные print() для понимания хода теста при отладке
3. **Покрытие**: Тесты покрывают не только happy path, но и граничные случаи и ошибки
4. **Безопасность**: Все тесты используют мок credentials, никогда не реальные

### Структура теста (Arrange-Act-Assert)

Каждый тест следует паттерну:
1. **Arrange** (Настройка): Подготовка моков и данных
2. **Act** (Действие): Выполнение тестируемого действия
3. **Assert** (Проверка): Верификация результата с явным сравнением

### Типы тестов

- **Unit-тесты**: Тестируют отдельные функции/классы в изоляции
- **Integration-тесты**: Проверяют взаимодействие компонентов
- **Security-тесты**: Верифицируют систему безопасности
- **Edge case-тесты**: Параноидальные проверки граничных случаев

## Добавление новых тестов

При добавлении новых тестов:

1. Следуйте существующей структуре классов (`Test*Success`, `Test*Errors`, `Test*EdgeCases`)
2. Используйте описательные имена: `test_<что_он_делает>_<ожидаемый_результат>`
3. Добавляйте docstring с "Что он делает" и "Цель"
4. Используйте print() для логирования шагов теста
5. Обновляйте этот README с описанием нового теста

## Troubleshooting

### Тесты падают с ImportError

```bash
# Убедитесь, что вы в корне проекта
cd /path/to/kiro-openai-gateway

# pytest.ini уже содержит pythonpath = .
# Просто запустите pytest
pytest
```

### Тесты проходят локально, но падают в CI

- Проверьте версии зависимостей в requirements.txt
- Убедитесь, что все моки корректно изолируют внешние вызовы

### Async тесты не работают

```bash
# Убедитесь, что pytest-asyncio установлен
pip install pytest-asyncio

# Проверьте наличие @pytest.mark.asyncio декоратора
```

## Метрики покрытия

Для проверки покрытия кода тестами:

```bash
# Установка coverage
pip install pytest-cov

# Запуск с отчетом о покрытии
pytest --cov=kiro_gateway --cov-report=html

# Просмотр отчета
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows
```

## Контакты и поддержка

При обнаружении багов или предложениях по улучшению тестов, создайте issue в репозитории проекта.