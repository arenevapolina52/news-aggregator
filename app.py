import sys
import os
from pathlib import Path

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

database_path = project_dir / 'news.db'
os.environ['DATABASE_URL'] = f'sqlite:///{database_path}'

try:
    from main import app
    application = app
    print("✅ Приложение успешно загружено")
except Exception as e:
    print(f"❌ Ошибка загрузки приложения: {e}")
    raise