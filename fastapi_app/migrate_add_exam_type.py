"""
Migration script to add exam_type column to generated_exams and exam_attempts tables.
"""
from sqlalchemy import text
from fastapi_app.database import engine

def run_migration():
    print("Starting database migration to add exam_type column...")
    
    with engine.connect() as conn:
        trans = conn.begin()
        
        try:
            # Add exam_type column to generated_exams
            print("Adding exam_type column to generated_exams...")
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'generated_exams' 
                        AND column_name = 'exam_type'
                    ) THEN
                        ALTER TABLE generated_exams 
                        ADD COLUMN exam_type VARCHAR NOT NULL DEFAULT 'cat';
                        
                        -- Update existing records based on exam_name
                        UPDATE generated_exams 
                        SET exam_type = CASE 
                            WHEN LOWER(exam_name) LIKE '%gate%' THEN 'gate'
                            WHEN LOWER(exam_name) = 'gate' THEN 'gate'
                            ELSE 'cat'
                        END;
                    END IF;
                END $$;
            """))
            
            # Add exam_type column to exam_attempts
            print("Adding exam_type column to exam_attempts...")
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'exam_attempts' 
                        AND column_name = 'exam_type'
                    ) THEN
                        ALTER TABLE exam_attempts 
                        ADD COLUMN exam_type VARCHAR NOT NULL DEFAULT 'cat';
                        
                        -- Update existing records based on exam_name
                        UPDATE exam_attempts 
                        SET exam_type = CASE 
                            WHEN LOWER(exam_name) LIKE '%gate%' THEN 'gate'
                            WHEN LOWER(exam_name) = 'gate' THEN 'gate'
                            ELSE 'cat'
                        END;
                    END IF;
                END $$;
            """))
            
            trans.commit()
            print("\n" + "="*60)
            print("Migration completed successfully!")
            print("Added exam_type column to both generated_exams and exam_attempts")
            print("="*60)
            
        except Exception as e:
            trans.rollback()
            print(f"\nERROR: Migration failed: {e}")
            raise

if __name__ == "__main__":
    run_migration()
