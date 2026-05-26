# Changelog

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версии следуют [Semantic Versioning](https://semver.org/lang/ru/).

## [0.1.2] - 2026-05-27

### Fixed

- Убрано нестандартное поле `protocol` из JSON-пакета.
- Добавлена диагностика ответа `Protocol != TCP` с рекомендацией изменить тип протокола прибора в настройках Narodmon.

## [0.1.1] - 2026-05-26

### Fixed

- TCP JSON теперь отправляется с завершающим переводом строки.
- HTTP(S) JSON endpoints изменены на `narodmon.com/json`, как в примере документации Narodmon.

## [0.1.0] - 2026-05-26

### Added

- Кастомная интеграция Home Assistant `narodmon`.
- Настройка через UI Home Assistant.
- Выбор сенсоров через multiple entity selector.
- Отправка JSON-пакетов Narodmon через TCP, HTTP и HTTPS.
- Режим одного виртуального прибора.
- Режим группировки по устройствам Home Assistant.
- Генерация MAC/ID виртуального прибора.
- Подготовка для установки через HACS.
