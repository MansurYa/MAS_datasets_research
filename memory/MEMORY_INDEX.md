# Memory Index

Индекс файлов памяти проекта (в `/Volumes/MansurSSD/MAS_datasets_research/memory/`).

| Файл | Описание | Когда читать |
|------|---------|------------|
| [TZ_STATUS.md](TZ_STATUS.md) | Статус всех TZ, текущая задача, структура репозитория | Каждая новая сессия |
| [feedback_file_structure.md](feedback_file_structure.md) | **КРИТИЧНО:** Правила работы с файловой структурой | **Перед любыми операциями с файлами** |
| [feedback_index_first.md](feedback_index_first.md) | Правило: всегда обновлять индексные файлы при изменениях | При любом изменении файловой структуры |
| [reference_mas_errors_pipeline.md](../memory/reference_mas_errors_pipeline.md) | GAP analysis и план решения 6+ проблем в MAS_errors pipeline | При работе с MAS_errors |
| [feedback_nebius_no_web_tools.md](feedback_nebius_no_web_tools.md) | nebius/SWE-agent не имеет веб-инструментов | При анализе nebius ошибок |
| [feedback_keyword_search_vs_structural.md](feedback_keyword_search_vs_structural.md) | Keyword search ловит code execution вместо tool invocation | При парсинге nebius ошибок |
| [feedback_venv.md](feedback_venv.md) | Использовать .venv для Python скриптов (система защищена) | Перед запуском любых Python скриптов |
| [reference_archive_map.md](reference_archive_map.md) | Полная карта archive/ — все ТЗ, скрипты, парсеры, зависимости | Когда нужен парсер или методология старого цикла |

**Примечание:** Автоматическая память Claude Code (feedback_language, reference_tau_retail) находится в `~/.claude/projects/.../memory/MEMORY.md`.