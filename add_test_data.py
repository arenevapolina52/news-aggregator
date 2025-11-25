from database import SessionLocal
import models
from datetime import datetime

def add_test_data():
    db = SessionLocal()
    try:
        print("🔄 Добавление тестовых данных...")
        
        # Добавляем категории
        categories = ["технологии", "политика", "спорт", "наука", "экономика"]
        for cat_name in categories:
            if not db.query(models.Category).filter(models.Category.name == cat_name).first():
                category = models.Category(name=cat_name)
                db.add(category)
                print(f"✅ Добавлена категория: {cat_name}")
        
        # Добавляем источники
        sources = [
            {"name": "Яндекс.Новости", "url": "https://news.yandex.ru"},
            {"name": "RSS Feed", "url": "https://example.com/rss"}
        ]
        for source_data in sources:
            if not db.query(models.Source).filter(models.Source.name == source_data["name"]).first():
                source = models.Source(**source_data)
                db.add(source)
                print(f"✅ Добавлен источник: {source_data['name']}")
        
        db.commit()
        
        # Получаем ID созданных категорий и источников
        technology_category = db.query(models.Category).filter(models.Category.name == "технологии").first()
        economy_category = db.query(models.Category).filter(models.Category.name == "экономика").first()
        sport_category = db.query(models.Category).filter(models.Category.name == "спорт").first()
        
        yandex_source = db.query(models.Source).filter(models.Source.name == "Яндекс.Новости").first()
        rss_source = db.query(models.Source).filter(models.Source.name == "RSS Feed").first()
        
        # Добавляем тестовые новости (БЕЗ поля source)
        test_news = [
            {
                "title": "Прорыв в искусственном интеллекте",
                "content": "Исследователи разработали новую модель ИИ, способную решать сложные задачи в области медицины и науки. Технология promises революционные изменения в диагностике заболеваний.",
                "url": "https://example.com/ai-breakthrough-1",
                "published_at": datetime.now(),
                "category_id": technology_category.id,
                "source_id": yandex_source.id
            },
            {
                "title": "Новые меры экономической поддержки", 
                "content": "Правительство анонсировало новые программы поддержки малого и среднего бизнеса на следующий год. Предполагается выделение дополнительных средств и льготное кредитование.",
                "url": "https://example.com/economy-news-1",
                "published_at": datetime.now(),
                "category_id": economy_category.id,
                "source_id": yandex_source.id
            },
            {
                "title": "Спортивные достижения сборной",
                "content": "Национальная сборная установила новый рекорд на международных соревнованиях по легкой атлетике. Спортсмены завоевали 5 золотых медалей.",
                "url": "https://example.com/sports-record-1", 
                "published_at": datetime.now(),
                "category_id": sport_category.id,
                "source_id": rss_source.id
            }
        ]
        
        for news_data in test_news:
            if not db.query(models.News).filter(models.News.url == news_data["url"]).first():
                news = models.News(**news_data)
                db.add(news)
                print(f"✅ Добавлена новость: {news_data['title']}")
        
        db.commit()
        print("🎉 Тестовые данные успешно добавлены!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_test_data()