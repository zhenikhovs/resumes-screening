# Факт: второй этап (cross-encoder rerank)

## Вход

- JSON первого этапа: `data/results/pipeline_transformer/<method>/` или `data/results/pipeline_classical/`.
- Исходные тексты:
  - для transformer-пайплайна — `cleaned/transformer`; для резюме берётся **`text_rerank`** (чуть больше опыта, чем в `text` для би-encoder), затем `append_experience_to_resume_text(..., for_rerank=True)` и `append_experience_to_vacancy_text`;
  - для classical-пайплайна — агрегированные строки `vacancy_to_text` / `resume_to_text` из `pipeline_classical.py`.

## Отбор кандидатов

Берутся только элементы из `candidates` (или эквивалентного списка), для которых  
`score_norm ≥ threshold`, где `threshold` — поле той же записи вакансии из первого этапа.

## Действие модели

Для каждой такой пары строится батч предсказаний `CrossEncoder.predict`; каждому кандидату присваивается **`rerank_score`**.

## Выход

Новый список **`cross_encoder_candidates`**: те же словари кандидатов (с прежними полями первого этапа плюс `rerank_score`), отсортированные по **`rerank_score` по убыванию**.

Если после порога кандидатов нет, `cross_encoder_candidates` — пустой массив.

## Имена файлов результатов

Выход: `data/results/pipeline_cross_encoder/<method>/cross_encoder_<method>_<query>.json` (см. [PIPELINE_COMMANDS.md](../PIPELINE_COMMANDS.md)).
