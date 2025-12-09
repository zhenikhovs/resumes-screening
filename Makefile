# Активировать виртуальное окружение и запустить проект
run:
	. venv/bin/activate && python3 main.py

# Установить зависимости
install:
	. venv/bin/activate && pip install -r requirements.txt

# Обновить pip
pip-upgrade:
	. venv/bin/activate && pip install --upgrade pip

# Очистить кэш Python
clean:
	rm -rf __pycache__ */__pycache__ 2>/dev/null || true

# Удалить данные
clean-data:
	rm -rf data/raw/*.json data/processed/*.json 2>/dev/null || true
