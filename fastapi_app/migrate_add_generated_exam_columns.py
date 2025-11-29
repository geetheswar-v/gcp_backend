"""
Migration script to add new columns to existing tables.
This adds the new GeneratedExam table and updates ExamAttempt table.
"""
from sqlalchemy import text
from fastapi_app.database import engine

def run_migration():
    print("Starting database migration...")
    
    with engine.connect() as conn:
        # Start a transaction
        trans = conn.begin()
        
        try:
            # 1. Create generated_exams table if it doesn't exist
            print("Creating generated_exams table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS generated_exams (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    exam_name VARCHAR NOT NULL,
                    stream VARCHAR,
                    year INTEGER,
                    generated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    exam_data JSON NOT NULL,
                    is_attempted BOOLEAN DEFAULT FALSE
                );
            """))
            
            # 2. Create index on user_id for generated_exams
            print("Creating index on generated_exams...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_generated_exams_user_id 
                ON generated_exams(user_id);
            """))
            
            # 3. Add generated_exam_id column to exam_attempts if it doesn't exist
            print("Adding generated_exam_id column to exam_attempts...")
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'exam_attempts' 
                        AND column_name = 'generated_exam_id'
                    ) THEN
                        ALTER TABLE exam_attempts 
                        ADD COLUMN generated_exam_id INTEGER REFERENCES generated_exams(id);
                    END IF;
                END $$;
            """))
            
            # 4. Add new statistics columns to exam_attempts if they don't exist
            print("Adding statistics columns to exam_attempts...")
            
            # total_questions
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'exam_attempts' 
                        AND column_name = 'total_questions'
                    ) THEN
                        ALTER TABLE exam_attempts 
                        ADD COLUMN total_questions INTEGER NOT NULL DEFAULT 0;
                    END IF;
                END $$;
            """))
            
            # correct_answers
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'exam_attempts' 
                        AND column_name = 'correct_answers'
                    ) THEN
                        ALTER TABLE exam_attempts 
                        ADD COLUMN correct_answers INTEGER NOT NULL DEFAULT 0;
                    END IF;
                END $$;
            """))
            
            # wrong_answers
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'exam_attempts' 
                        AND column_name = 'wrong_answers'
                    ) THEN
                        ALTER TABLE exam_attempts 
                        ADD COLUMN wrong_answers INTEGER NOT NULL DEFAULT 0;
                    END IF;
                END $$;
            """))
            
            # unanswered
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'exam_attempts' 
                        AND column_name = 'unanswered'
                    ) THEN
                        ALTER TABLE exam_attempts 
                        ADD COLUMN unanswered INTEGER NOT NULL DEFAULT 0;
                    END IF;
                END $$;
            """))
            
            # percentage
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'exam_attempts' 
                        AND column_name = 'percentage'
                    ) THEN
                        ALTER TABLE exam_attempts 
                        ADD COLUMN percentage INTEGER;
                    END IF;
                END $$;
            """))
            
            # time_taken
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'exam_attempts' 
                        AND column_name = 'time_taken'
                    ) THEN
                        ALTER TABLE exam_attempts 
                        ADD COLUMN time_taken INTEGER;
                    END IF;
                END $$;
            """))
            
            trans.commit()
            print("\n" + "="*60)
            print("Migration completed successfully!")
            print("="*60)
            
        except Exception as e:
            trans.rollback()
            print(f"\nERROR: Migration failed: {e}")
            raise

if __name__ == "__main__":
    run_migration()
