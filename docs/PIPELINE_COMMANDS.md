# Команды запуска: pipeline и cross-encoder

Запуск из **корня проекта**: `python run.py <command> [опции]`.

---

## 1. Классический pipeline (BM25)

Один этап: фильтр по опыту → BM25 similarity → min-max → 90% порог → top-10.

```bash
python run.py pipeline_ranking --classical
```

Результаты: `data/results/pipeline_classical/pipeline_classical_<query>.json`.

---

## 2. Transformer pipeline (первый этап, bi-encoder)

По одному запуску на каждую модель: e5, minilm, ru_sbert, mpnet.

```bash
python run.py pipeline_ranking --transformer --transformer-method e5
python run.py pipeline_ranking --transformer --transformer-method minilm
python run.py pipeline_ranking --transformer --transformer-method ru_sbert
python run.py pipeline_ranking --transformer --transformer-method mpnet
```

Результаты: `data/results/pipeline_transformer/<method>/pipeline_<method>_<query>.json`.

---

## 3. Cross-encoder rerank (второй этап)

Запускать **после** того, как есть результаты transformer-pipeline для нужного `--transformer-method`.

Доступные cross-encoder по ключу `--model`:

| Ключ           | Модель                                            | Описание                           |
| -------------- | ------------------------------------------------- | ---------------------------------- |
| `russian`      | DiTy/cross-encoder-russian-msmarco                | Для русского текста (по умолчанию) |
| `minilm`       | cross-encoder/ms-marco-MiniLM-L-6-v2              | Лёгкая, быстрая                    |
| `multilingual` | cross-encoder/ms-marco-Multilingual-MiniLM-L12-v2 | Мультиязычная                      |

### Запуск для всех трёх cross-encoder (на примере ru_sbert)

```bash
# Русская cross-encoder (по умолчанию)
python run.py pipeline_rerank --transformer-method ru_sbert --model russian

# Лёгкая cross-encoder
python run.py pipeline_rerank --transformer-method ru_sbert --model minilm

# Мультиязычная cross-encoder
python run.py pipeline_rerank --transformer-method ru_sbert --model multilingual
```

Результаты:  
`data/results/pipeline_cross_encoder/<transformer_method>/cross_encoder_<method>_<russian|minilm|multilingual>_<query>.json`.

### То же для других transformer-методов

Подставьте нужный метод: `e5`, `minilm`, `ru_sbert`, `mpnet`.

```bash
python run.py pipeline_rerank --transformer-method e5      --model russian
python run.py pipeline_rerank --transformer-method e5      --model minilm
python run.py pipeline_rerank --transformer-method e5      --model multilingual

python run.py pipeline_rerank --transformer-method minilm  --model russian
python run.py pipeline_rerank --transformer-method minilm  --model minilm
python run.py pipeline_rerank --transformer-method minilm  --model multilingual

python run.py pipeline_rerank --transformer-method ru_sbert --model russian
python run.py pipeline_rerank --transformer-method ru_sbert --model minilm
python run.py pipeline_rerank --transformer-method ru_sbert --model multilingual

python run.py pipeline_rerank --transformer-method mpnet   --model russian
python run.py pipeline_rerank --transformer-method mpnet   --model minilm
python run.py pipeline_rerank --transformer-method mpnet   --model multilingual
```

### Свой батч и своя модель

```bash
python run.py pipeline_rerank --transformer-method ru_sbert --model russian --batch-size 64
python run.py pipeline_rerank --transformer-method ru_sbert --model-name cross-encoder/другая-модель --batch-size 32
```

---

## 4. Полная последовательность для сравнения cross-encoder

1. Запустить первый этап для одного или нескольких transformer-методов (например, ru_sbert):

   ```bash
   python run.py pipeline_ranking --transformer --transformer-method ru_sbert
   ```

2. Запустить rerank для всех трёх cross-encoder:

   ```bash
   python run.py pipeline_rerank --transformer-method ru_sbert --model russian
   python run.py pipeline_rerank --transformer-method ru_sbert --model minilm
   python run.py pipeline_rerank --transformer-method ru_sbert --model multilingual
   ```

3. Сравнить файлы в `data/results/pipeline_cross_encoder/ru_sbert/`:
   - `cross_encoder_ru_sbert_russian_<query>.json`
   - `cross_encoder_ru_sbert_minilm_<query>.json`
   - `cross_encoder_ru_sbert_multilingual_<query>.json`
