# migrate.py
import asyncio
from sqlalchemy import text
from backend.app.api.database import engine, Base

async def run_migration():
    """Запустить миграцию"""
    async with engine.begin() as conn:
        print("🔄 Создаем таблицы...")
        
        # Создаем таблицу telegram_status
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS telegram_status (
                telegram_id VARCHAR PRIMARY KEY,
                jwt_token TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                is_used BOOLEAN NOT NULL DEFAULT FALSE
            );
        """))
        print("✅ Таблица telegram_status создана")
        
        # Создаем индекс
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_telegram_status_created_at_used 
            ON telegram_status(created_at, is_used);
        """))
        
        # Добавляем колонку google_email в users
        await conn.execute(text("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='users' AND column_name='google_email'
                ) THEN
                    ALTER TABLE users ADD COLUMN google_email VARCHAR;
                END IF;
            END $$;
        """))
        print("✅ Колонка google_email в users добавлена")
        
        # Создаем индекс для google_email
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_users_google_email ON users(google_email);
        """))
        
        # Добавляем колонку google_email в oauth_tokens
        await conn.execute(text("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='oauth_tokens' AND column_name='google_email'
                ) THEN
                    ALTER TABLE oauth_tokens ADD COLUMN google_email VARCHAR;
                END IF;
            END $$;
        """))
        print("✅ Колонка google_email в oauth_tokens добавлена")
        
        # Меняем тип колонок для токенов (если нужно)
        await conn.execute(text("""
            ALTER TABLE oauth_tokens 
            ALTER COLUMN refresh_token TYPE TEXT,
            ALTER COLUMN access_token TYPE TEXT;
        """))
        print("✅ Типы колонок обновлены")
        
        # Создаем индекс для google_email
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_oauth_tokens_google_email 
            ON oauth_tokens(google_email);
        """))
        
        print("🎉 Миграция завершена успешно!")

if __name__ == "__main__":
    asyncio.run(run_migration())