# Факт: алгоритм первого этапа (как в коде)

Источник: `config/pipeline_config.py`, `services/ranking/pipeline_common.py`, `pipeline_classical.py`, `pipeline_transformer.py`.

---

## 1. Опыт: два правила

**Вход в пул (фильтр):**  
`resume.total_experience_months ≥ ⌊0.8 × vacancy.min_experience_months⌋` (`EXPERIENCE_FACTOR = 0.8`).  
Не прошедшие не участвуют в similarity.

**experience_match (в формуле score):**  
`1`, если `resume.total_experience_months ≥ vacancy.min_experience_months` (полный минимум, без 0.8);  
`0`, если в пуле только за счёт мягкого порога, но полный минимум не набран.  
Если `min_experience_months` не задан (0), у допущенных в пул `experience_match = 1`.

---

## 2. Similarity

**BM25 / TF-IDF:** токены текстов classical; min–max по N кандидатам вакансии.

**Transformer:** эмбеддинги поля `text` резюме (короткий конспект + при encode дописываются месяцы стажа). E5: префиксы `query:` / `passage:`.

Classical **не** использует `append_experience_to_*`.

---

## 3. Итоговый score

\[
\text{final\_score} = 0{.}9 \times \text{similarity} + 0{.}1 \times \text{experience\_match}
\]

Затем min–max по вакансии → `score_norm`.

---

## 4. Порог и top-K

`threshold = P_{90}(score_norm)`, в `top_k_candidates` — до 10 с `score_norm ≥ threshold`.  
В JSON у кандидата есть поле `experience_match`.

Подмножество после порога идёт во второй этап (cross-encoder на `text_rerank`).
