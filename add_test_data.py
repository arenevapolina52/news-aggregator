from database import SessionLocal
import models
from datetime import datetime
from auth import get_password_hash

def add_test_data():
    db = SessionLocal()
    try:
        print("🔄 Добавление тестовых данных...")
        
        # Проверяем, нет ли уже пользователя
        existing_user = db.query(models.User).filter(models.User.email == "test@example.com").first()
        if not existing_user:
            # Добавляем тестового пользователя с ХЕШИРОВАННЫМ паролем
            test_user = models.User(
                email="test@example.com",
                username="testuser", 
                hashed_password=get_password_hash("password123")  # ✅ Теперь хешированный
            )
            db.add(test_user)
            print("✅ Добавлен тестовый пользователь")
        
        # Добавляем тестовые новости
        test_news = [
            {
                "title": "Прорыв в искусственном интеллекте",
                "summary": "Исследователи разработали новую модель ИИ, способную решать сложные задачи в области медицины и науки.",
                "source": "Яндекс.Новости",
                "category": "технологии",
                "url": "https://example.com/ai-breakthrough-1"
            },
            {
                "title": "Новые меры экономической поддержки", 
                "summary": "Правительство анонсировало новые программы поддержки малого и среднего бизнеса.",
                "source": "РБК",
                "category": "экономика",
                "url": "https://example.com/economy-news-1"
            },
            {
                "title": "Спортивные достижения сборной",
                "summary": "Национальная сборная установила новый рекорд на международных соревнованиях.",
                "source": "Спорт-Экспресс",
                "category": "спорт", 
                "url": "https://example.com/sports-record-1"
            },
            {
                "title": "Культурные события недели",
                "summary": "В столице открылась новая выставка современного искусства.",
                "source": "Культура",
                "category": "культура",
                "url": "https://example.com/culture-news-1"
            }
        ]
        
        added_count = 0
        for news_data in test_news:
            if not db.query(models.NewsArticle).filter(models.NewsArticle.url == news_data["url"]).first():
                news = models.NewsArticle(
                    title=news_data["title"],
                    summary=news_data["summary"],
                    source=news_data["source"],
                    category=news_data["category"],
                    url=news_data["url"],
                    published_at=datetime.now()
                )
                db.add(news)
                added_count += 1
                print(f"✅ Добавлена новость: {news_data['title']}")
        
        db.commit()
        print(f"🎉 Тестовые данные успешно добавлены! Добавлено {added_count} новостей")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_test_data()