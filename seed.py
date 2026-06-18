import os
from database.connection import SessionLocal
from dal.repositories import ScenarioRepository, UserRepository
from dal.models import Scenario

def seed_data():
    session = SessionLocal()
    scenario_repo = ScenarioRepository(session)
    user_repo = UserRepository(session)

    print("=== Инициализация начальных данных (Data Seeding) ===")

    #Наполнение таблицы scenarios
    required_scenarios = [
        {
            "title": "Инвентарный анализ",
            "description": "Комплексный анализ запасов: ABC (по выручке), XYZ (по стабильности спроса), прогноз категорий анализа 3-мя методами, метрика safety stock."
        },
        {
            "title": "RFM-анализ",
            "description": "Сегментация клиентской базы по RFM, LTV-прогноз и маркетинговые рекомендации"
        },
        {
            "title": "Финансовый скоринг",
            "description": "Скоринг дебиторской задолженности, расчёт Expected Loss и рекомендации по кредитным лимитам"
        }
    ]

    for sc_data in required_scenarios:
        # Проверяем по точному названию title, чтобы избежать дублирования
        existing = session.query(Scenario).filter_by(title=sc_data["title"]).first()
        if not existing:
            scenario_repo.create(sc_data["title"], sc_data["description"])
            print(ax_msg := f"Добавлен сценарий: {sc_data['title']}")
        else:
            print(f"Сценарий уже существует: {sc_data['title']} (пропуск)")

            
    session.commit()
    session.close()
    print("=== Инициализация успешно завершена ===\n")

if __name__ == "__main__":
    seed_data()