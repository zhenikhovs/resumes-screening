import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass, asdict, field
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import time
import json
import csv
from datetime import datetime

QUERIES = [
    "web developer",
    "frontend developer",
    "php developer",
    "IT project manager",
    "javascript developer",
    "backend developer",
    "fullstack developer",
    "project manager"
]


@dataclass
class MatchResult:
    query: str
    vacancy_id: str
    resume_id: str
    similarity_score: float
    vacancy_preview: str = ""
    resume_preview: str = ""


@dataclass
class QueryMatchResults:
    query: str
    method: str
    top_matches: List[MatchResult] = field(default_factory=list)
    average_similarity: float = 0.0
    total_vacancies: int = 0
    total_resumes: int = 0


class JobMatcher:
    def __init__(self,
                 resumes_dir: str = "data/prepared/resumes/cleaned/",
                 vacancies_dir: str = "data/prepared/vacancies/cleaned/"):
        self.resumes_dir = Path(resumes_dir)
        self.vacancies_dir = Path(vacancies_dir)
        self.methods = ["classical", "transformer"]
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.8
        )
        self.all_results: Dict[str, Dict[str, QueryMatchResults]] = {}  # {method: {query: results}}

    def _load_json_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Загрузить JSON файл."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                # Проверяем формат данных
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and 'items' in data:
                    return data['items']
                elif isinstance(data, dict) and 'data' in data:
                    return data['data']
                else:
                    print(f"Неожиданный формат в файле {file_path.name}")
                    return []
        except Exception as e:
            print(f"Ошибка чтения файла {file_path}: {e}")
            return []

    def _extract_text(self, item: Dict[str, Any]) -> str:
        """Извлечь текст из объекта резюме/вакансии."""
        # Пробуем различные ключи, которые могут содержать текст
        text_keys = ['text', 'description', 'content', 'cleaned_text',
                     'full_text', 'resume_text', 'vacancy_text']

        for key in text_keys:
            if key in item and isinstance(item[key], str):
                return item[key].strip()

        # Если не нашли текстовые ключи, пробуем объединить все строковые поля
        text_parts = []
        for key, value in item.items():
            if isinstance(value, str) and len(value.strip()) > 0:
                text_parts.append(value.strip())

        return " ".join(text_parts)

    def _extract_id(self, item: Dict[str, Any]) -> str:
        """Извлечь ID из объекта."""
        id_keys = ['id', '_id', 'uid', 'vacancy_id', 'resume_id', 'file_name']

        for key in id_keys:
            if key in item and item[key]:
                return str(item[key])

        # Если ID нет, создаем хеш из текста
        text = self._extract_text(item)
        return str(hash(text))[:10]

    def process_query(self, query: str, method: str) -> QueryMatchResults:
        """Обработать один запрос для указанного метода."""
        print(f"  Обработка {query} ({method})...")

        # Загружаем данные
        resumes_file = self.resumes_dir / method / f"resumes_{query.replace(' ', '_')}.json"
        vacancies_file = self.vacancies_dir / method / f"vacancies_{query.replace(' ', '_')}.json"

        # Проверяем существование файлов
        if not resumes_file.exists():
            print(f"    Файл резюме не найден: {resumes_file}")
            return QueryMatchResults(query=query, method=method)

        if not vacancies_file.exists():
            print(f"    Файл вакансий не найден: {vacancies_file}")
            return QueryMatchResults(query=query, method=method)

        # Загружаем данные
        resumes_data = self._load_json_file(resumes_file)
        vacancies_data = self._load_json_file(vacancies_file)

        print(f"    Вакансий: {len(vacancies_data)}, Резюме: {len(resumes_data)}")

        if not vacancies_data or not resumes_data:
            return QueryMatchResults(
                query=query,
                method=method,
                total_vacancies=len(vacancies_data),
                total_resumes=len(resumes_data)
            )

        # Извлекаем тексты и ID
        resumes_texts = []
        resumes_ids = []
        resumes_previews = []

        for resume in resumes_data:
            text = self._extract_text(resume)
            if text and len(text) > 10:  # Проверяем, что текст не пустой
                resumes_texts.append(text)
                resumes_ids.append(self._extract_id(resume))
                resumes_previews.append(text[:200] + "..." if len(text) > 200 else text)

        vacancies_texts = []
        vacancies_ids = []
        vacancies_previews = []

        for vacancy in vacancies_data:
            text = self._extract_text(vacancy)
            if text and len(text) > 10:
                vacancies_texts.append(text)
                vacancies_ids.append(self._extract_id(vacancy))
                vacancies_previews.append(text[:200] + "..." if len(text) > 200 else text)

        # Векторизация
        all_texts = vacancies_texts + resumes_texts
        tfidf_matrix = self.vectorizer.fit_transform(all_texts)

        # Разделяем матрицу на вакансии и резюме
        vacancy_vectors = tfidf_matrix[:len(vacancies_texts)]
        resume_vectors = tfidf_matrix[len(vacancies_texts):]

        # Вычисляем попарные схожести
        similarity_matrix = cosine_similarity(vacancy_vectors, resume_vectors)

        # Собираем все пары
        all_matches = []
        for i, vacancy_id in enumerate(vacancies_ids):
            for j, resume_id in enumerate(resumes_ids):
                score = similarity_matrix[i, j]
                all_matches.append(MatchResult(
                    query=query,
                    vacancy_id=vacancy_id,
                    resume_id=resume_id,
                    similarity_score=float(score),
                    vacancy_preview=vacancies_previews[i],
                    resume_preview=resumes_previews[j]
                ))

        # Сортируем по убыванию схожести
        all_matches.sort(key=lambda x: x.similarity_score, reverse=True)

        # Берем топ-20 результатов
        top_matches = all_matches[:20]

        # Вычисляем среднюю схожесть
        avg_similarity = np.mean(similarity_matrix) if similarity_matrix.size > 0 else 0.0

        return QueryMatchResults(
            query=query,
            method=method,
            top_matches=top_matches,
            average_similarity=float(avg_similarity),
            total_vacancies=len(vacancies_texts),
            total_resumes=len(resumes_texts)
        )

    def match_all(self) -> Dict[str, Dict[str, QueryMatchResults]]:
        """Сравнить все вакансии и резюме по всем запросам и методам."""
        print("Запуск сравнения вакансий и резюме...")
        start_time = time.time()

        all_results = {}

        for method in self.methods:
            print(f"\nМетод: {method}")
            method_results = {}

            for query in QUERIES:
                result = self.process_query(query, method)
                method_results[query] = result

            all_results[method] = method_results

        elapsed_time = time.time() - start_time
        print(f"\nЗавершено за {elapsed_time:.2f} секунд")

        self.all_results = all_results
        return all_results

    def save_results_json(self, output_dir: str = "results"):
        """Сохранить результаты в JSON файлы."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Сохраняем сводный отчет
        summary = {}
        for method in self.methods:
            summary[method] = {}
            for query in QUERIES:
                if query in self.all_results[method]:
                    results = self.all_results[method][query]
                    summary[method][query] = {
                        "total_vacancies": results.total_vacancies,
                        "total_resumes": results.total_resumes,
                        "average_similarity": results.average_similarity,
                        "top_matches_count": len(results.top_matches)
                    }

        summary_file = output_path / f"summary_{timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        # Сохраняем детальные результаты для каждого метода
        for method in self.methods:
            method_dir = output_path / method
            method_dir.mkdir(exist_ok=True)

            for query in QUERIES:
                if query in self.all_results[method]:
                    results = self.all_results[method][query]

                    result_dict = {
                        "query": results.query,
                        "method": results.method,
                        "total_vacancies": results.total_vacancies,
                        "total_resumes": results.total_resumes,
                        "average_similarity": results.average_similarity,
                        "top_matches": [
                            {
                                "vacancy_id": match.vacancy_id,
                                "resume_id": match.resume_id,
                                "similarity_score": match.similarity_score,
                                "vacancy_preview": match.vacancy_preview,
                                "resume_preview": match.resume_preview
                            }
                            for match in results.top_matches
                        ]
                    }

                    query_safe = query.replace(' ', '_').replace('/', '_')
                    result_file = method_dir / f"{query_safe}_matches.json"

                    with open(result_file, 'w', encoding='utf-8') as f:
                        json.dump(result_dict, f, ensure_ascii=False, indent=2)

        print(f"Результаты сохранены в директории: {output_path}")

    def save_results_csv(self, output_dir: str = "results"):
        """Сохранить результаты в CSV файлы."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Сохраняем все совпадения в один CSV
        all_matches_file = output_path / f"all_matches_{timestamp}.csv"
        with open(all_matches_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Method', 'Query', 'Vacancy_ID', 'Resume_ID',
                             'Similarity_Score', 'Vacancy_Preview', 'Resume_Preview'])

            for method in self.methods:
                for query in QUERIES:
                    if query in self.all_results[method]:
                        for match in self.all_results[method][query].top_matches:
                            writer.writerow([
                                method,
                                query,
                                match.vacancy_id,
                                match.resume_id,
                                f"{match.similarity_score:.4f}",
                                match.vacancy_preview[:100],
                                match.resume_preview[:100]
                            ])

        # Сохраняем сводную статистику
        summary_file = output_path / f"summary_{timestamp}.csv"
        with open(summary_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Method', 'Query', 'Total_Vacancies', 'Total_Resumes',
                             'Average_Similarity', 'Top_Matches_Count'])

            for method in self.methods:
                for query in QUERIES:
                    if query in self.all_results[method]:
                        results = self.all_results[method][query]
                        writer.writerow([
                            method,
                            query,
                            results.total_vacancies,
                            results.total_resumes,
                            f"{results.average_similarity:.4f}",
                            len(results.top_matches)
                        ])

        print(f"CSV файлы сохранены в: {output_path}")

    def print_summary(self):
        """Вывести сводку результатов."""
        print("\n" + "=" * 80)
        print("СВОДКА РЕЗУЛЬТАТОВ")
        print("=" * 80)

        for method in self.methods:
            print(f"\nМетод: {method}")
            print("-" * 40)

            for query in QUERIES:
                if query in self.all_results[method]:
                    results = self.all_results[method][query]

                    if results.total_vacancies > 0 and results.total_resumes > 0:
                        print(f"\n  {query}:")
                        print(f"    Вакансий: {results.total_vacancies}, Резюме: {results.total_resumes}")
                        print(f"    Средняя схожесть: {results.average_similarity:.3f}")

                        if results.top_matches:
                            print(f"    Лучшее совпадение: {results.top_matches[0].similarity_score:.3f}")
                            print(f"      Вакансия: {results.top_matches[0].vacancy_id[:20]}...")
                            print(f"      Резюме: {results.top_matches[0].resume_id[:20]}...")
                    else:
                        print(f"\n  {query}: Нет данных или недостаточно данных для сравнения")

    def get_best_overall_matches(self, min_score: float = 0.5, top_n: int = 10) -> List[MatchResult]:
        """Получить лучшие совпадения по всем методам и запросам."""
        all_best = []

        for method in self.methods:
            for query in QUERIES:
                if query in self.all_results[method]:
                    for match in self.all_results[method][query].top_matches:
                        if match.similarity_score >= min_score:
                            all_best.append(match)

        # Сортируем по схожести
        all_best.sort(key=lambda x: x.similarity_score, reverse=True)
        return all_best[:top_n]


def main():
    # Инициализация матчера
    matcher = JobMatcher()

    # Проверяем существование директорий
    if not matcher.resumes_dir.exists():
        print(f"Ошибка: Директория резюме не существует: {matcher.resumes_dir}")
        return

    if not matcher.vacancies_dir.exists():
        print(f"Ошибка: Директория вакансий не существует: {matcher.vacancies_dir}")
        return

    # Выполняем сравнение
    results = matcher.match_all()

    # Выводим сводку
    matcher.print_summary()

    # Сохраняем результаты
    matcher.save_results_json()
    matcher.save_results_csv()

    # Выводим лучшие совпадения
    print("\n" + "=" * 80)
    print("ЛУЧШИЕ ОБЩИЕ СОВПАДЕНИЯ (схожесть > 0.6):")
    print("=" * 80)

    best_matches = matcher.get_best_overall_matches(min_score=0.6, top_n=15)
    for i, match in enumerate(best_matches, 1):
        print(f"\n{i}. [{match.method}] {match.query}")
        print(f"   Схожесть: {match.similarity_score:.3f}")
        print(f"   Вакансия ID: {match.vacancy_id}")
        print(f"   Резюме ID: {match.resume_id}")
        print(f"   Вакансия: {match.vacancy_preview[:150]}...")
        print(f"   Резюме: {match.resume_preview[:150]}...")


if __name__ == "__main__":
    main()