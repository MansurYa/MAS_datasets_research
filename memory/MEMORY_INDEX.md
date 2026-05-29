# Memory Index

Индекс файлов памяти проекта (в `/Volumes/MansurSSD/MAS_datasets_research/memory/`).

| Файл | Описание | Когда читать |
|------|---------|------------|
| [TZ_STATUS.md](TZ_STATUS.md) | Статус всех TZ, текущая задача, структура репозитория | Каждая новая сессия |
| [feedback_file_structure.md](feedback_file_structure.md) | **КРИТИЧНО:** Правила работы с файловой структурой | **Перед любыми операциями с файлами** |
| [feedback_index_first.md](feedback_index_first.md) | Правило: всегда обновлять индексные файлы при изменениях | При любом изменении файловой структуры |
| [reference_archive_map.md](reference_archive_map.md) | Полная карта archive/ — все ТЗ, скрипты, парсеры, зависимости | Когда нужен парсер или методология старого цикла |
| [feedback_venv.md](feedback_venv.md) | Использовать .venv для Python скриптов (система защищена) | Перед запуском любых Python скриптов |

**Примечание:** Автоматическая память Claude Code (feedback_language, reference_tau_retail) находится в `~/.claude/projects/.../memory/MEMORY.md`.