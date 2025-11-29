import chromadb
from sentence_transformers import SentenceTransformer
import json
import os
import random
import asyncio
import google.generativeai as genai
import requests
from datetime import datetime

# --- Configuration ---
BASE_APP_DATA_PATH = './app_data'
MODEL_NAME = 'all-MiniLM-L6-v2'
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama") # 'gemini' or 'ollama'
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "granite4:3b-h")

def get_exam_paths(exam_type):
    """Get paths for vector DB, questions, and generated exams based on exam type"""
    return {
        'vector_db': os.path.join(BASE_APP_DATA_PATH, 'vector_db', exam_type.upper()),
        'structured_questions': os.path.join(BASE_APP_DATA_PATH, 'structured_questions', exam_type.upper()),
        'generated_exams': os.path.join(BASE_APP_DATA_PATH, 'generated_questions', exam_type.upper())
    }

# Structure of supported exams to be generated
SUPPORTED_EXAMS = {
    "CAT": {
        "varc": {"mcq": 21, "tita": 3},
        "dilr": {"mcq": 12, "tita": 10},
        "quant": {"mcq": 14, "tita": 8}
    },
    "GATE": {
        # Common structure for all GATE streams
        # Each stream has 65 questions: 10 GA (General Aptitude) + 55 Technical
        "general_aptitude": {"mcq": 10, "tita": 0},
        "technical": {"mcq": 45, "tita": 10}
    }
}

# All 30 GATE streams as of 2024
GATE_STREAMS = [
    "AE", "AG", "AR", "BM", "BT", "CE", "CH", "CS", "CY", "DA",
    "EC", "EE", "EN", "ES", "EY", "GE", "GG", "IN", "MA", "ME",
    "MN", "MT", "NM", "PE", "PH", "PI", "ST", "TF", "XE", "XL"
]

# Mapping for section names to filename abbreviations
SECTION_FILENAME_MAP = {
    # CAT sections
    "varc": "VARC",
    "dilr": "DILR",
    "quant": "QA",
    # GATE sections
    "general_aptitude": "GA",
    "technical": "TECH"
}

class RAGService:
    def __init__(self, exam_type="CAT"):
        self.exam_type = exam_type.upper()
        self.paths = get_exam_paths(self.exam_type)
        
        print(f"Initializing RAG Service for {self.exam_type} exam...")
        print(f"Loading vector database from: {self.paths['vector_db']}")
        
        # Ensure directories exist
        os.makedirs(self.paths['vector_db'], exist_ok=True)
        os.makedirs(self.paths['structured_questions'], exist_ok=True)
        os.makedirs(self.paths['generated_exams'], exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=self.paths['vector_db'])

        # Diagnostic check for existing collections
        print("\n--- Vector DB Collection Summary ---")
        try:
            collections = self.client.list_collections()
            if collections:
                print(f"Found {len(collections)} collections: {[c.name for c in collections]}")
            else:
                print("No collections found. Please run 'build_vector_db.py' to create them.")
        except Exception as e:
            print(f"Could not connect to or list collections in ChromaDB: {e}")
            print("Please ensure the vector database has been built correctly.")
        print("------------------------------------\n")

        print(f"Loading sentence transformer model: {MODEL_NAME}")
        self.model = SentenceTransformer(MODEL_NAME)

        self.source_questions = self._load_source_questions()

        # Gemini model attributes (lazy initialization)
        self._gemini_model = None
        self._gemini_model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

        # Diagnostic summary to check loaded data
        print("\n--- Source Data Summary ---")
        for section, questions in self.source_questions.items():
            if not questions:
                print(f"Section {section.upper()}: 0 questions loaded. Please check the source JSON file.")
                continue
            mcq_count = sum(1 for q in questions if 'option1' in q)
            tita_count = sum(1 for q in questions if 'option1' not in q)
            print(f"Section {section.upper()}: Loaded {len(questions)} total questions ({mcq_count} MCQ, {tita_count} TITA).")
        print("---------------------------\n")

        print("RAG Service initialized successfully.")

    def _load_source_questions(self):
        """
        Loads all questions from the JSON files into memory for quick lookups.
        Handles both CAT and GATE exam formats.
        """
        source_data = {}
        exam_sections = SUPPORTED_EXAMS.get(self.exam_type, {}).keys()
        
        for section in exam_sections:
            file_abbr = SECTION_FILENAME_MAP.get(section, section.upper())
            file_name = f"{self.exam_type}_{file_abbr}_all_years_combined.json"
            file_path = os.path.join(self.paths['structured_questions'], file_name)
            
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        source_data[section] = data if isinstance(data, list) else []
                except json.JSONDecodeError:
                    print(f"Warning: Could not decode JSON from {file_path}.")
                    source_data[section] = []
            else:
                source_data[section] = []
                print(f"Warning: Source JSON file not found at '{file_path}'")
        return source_data

    def _find_seed_question(self, section, q_type, exam_name, stream, year):
        """Finds a random question that matches the specified filters to seed the search."""
        candidates = self.source_questions.get(section, [])
        
        # Filter by exam first
        if exam_name:
            candidates = [q for q in candidates if q.get('exam', '').lower() == exam_name.lower()]
        
        # For GATE, handle GA vs Technical sections differently
        if exam_name and exam_name.upper() == "GATE":
            if section == "general_aptitude":
                # GA questions are shared across all streams, don't filter by stream
                pass
            elif section == "technical" and stream:
                # Technical questions are stream-specific
                candidates = [q for q in candidates if q.get('stream', '').lower() == stream.lower()]
        elif stream:
            # For other exams, filter by stream if provided
            candidates = [q for q in candidates if q.get('stream', '').lower() == stream.lower()]
            
        # Filter by year if provided
        if year:
            candidates = [q for q in candidates if q.get('year') == year]

        # Filter by question type
        if q_type == 'mcq':
            filtered = [q for q in candidates if 'option1' in q]
        else: # TITA
            filtered = [q for q in candidates if 'option1' not in q]

        return random.choice(filtered) if filtered else None

    def _ensure_gemini_model(self):
        """
        Lazily instantiate and configure the Gemini model.
        Returns the model instance or None if configuration failed.
        """
        if getattr(self, "_gemini_model", None):
            return self._gemini_model

        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_api_key:
            print("Warning: GEMINI_API_KEY not set. Gemini generation is unavailable.")
            return None

        model_name = os.environ.get("GEMINI_MODEL", self._gemini_model_name)
        try:
            genai.configure(api_key=gemini_api_key)
            self._gemini_model = genai.GenerativeModel(model_name)
            self._gemini_model_name = model_name
            return self._gemini_model
        except Exception as exc:
            print(f"Error initializing Gemini model '{model_name}': {exc}")
            return None

    @staticmethod
    def _extract_gemini_text(response):
        """
        Extract the textual payload from a Gemini response object.
        """
        if not response:
            return ""

        if getattr(response, "text", None):
            return response.text

        parts = []
        for candidate in getattr(response, "candidates", []):
            content = getattr(candidate, "content", None)
            if not content:
                continue
            for part in getattr(content, "parts", []):
                text = getattr(part, "text", "")
                if text:
                    parts.append(text)

        return "\n".join(parts).strip()

    async def _generate_single_question(self, section, q_type, exam_name, stream, year):
        """Generates one new question using the RAG pipeline with Gemini API."""
        seed_question = self._find_seed_question(section, q_type, exam_name, stream, year)
        if not seed_question:
            return {"error": f"No seed questions found for {exam_name} {stream or ''} {year or ''} - {section} {q_type}"}

        # Handle collection naming for both CAT and GATE
        if self.exam_type == "CAT":
            collection_abbr = 'qa' if section == 'quant' else section
            collection_name = f"cat_{collection_abbr}_all_years_combined"
        else:  # GATE
            if section == "technical":
                # For GATE technical questions, use stream-specific collection
                collection_name = f"gate_{stream.lower()}_technical_all_years_combined"
            else:  # general_aptitude
                collection_name = f"gate_ga_all_years_combined"

        try:
            collection = self.client.get_collection(name=collection_name)
            retrieved_results = collection.query(
                query_texts=[seed_question['question_text']],
                n_results=3 
            )
            
            context_questions = retrieved_results['documents'][0]
            prompt = self._create_llm_prompt(section, q_type, context_questions)
            
            if LLM_PROVIDER == 'ollama':
                try:
                    response_text = await self._invoke_ollama(prompt)
                    llm_text = response_text
                except Exception as e:
                    return {"error": f"Ollama API Error: {e}"}
            else:
                gemini_model = self._ensure_gemini_model()
                if not gemini_model:
                    return {"error": "Gemini API Key not found. Please set the GEMINI_API_KEY environment variable."}

                generation_config = {
                    "temperature": 0.7,
                    "max_output_tokens": 4096,
                    "response_mime_type": "application/json"
                }

                def _invoke_gemini():
                    return gemini_model.generate_content(
                        prompt,
                        generation_config=generation_config
                    )

                try:
                    response = await asyncio.to_thread(_invoke_gemini)
                    llm_text = self._extract_gemini_text(response) or "{}"
                except Exception as exc:
                    return {"error": f"Gemini API Error: {exc}"}

            try:
                # Clean up potential markdown code blocks from Ollama
                if "```json" in llm_text:
                    llm_text = llm_text.split("```json")[1].split("```")[0].strip()
                elif "```" in llm_text:
                    llm_text = llm_text.split("```")[1].split("```")[0].strip()
                
                generated_q = json.loads(llm_text)
                generated_q['section'] = SECTION_FILENAME_MAP.get(section, section.upper())
                generated_q['type'] = q_type.upper()
                return generated_q
            except json.JSONDecodeError:
                return {"error": "Failed to parse LLM JSON response", "raw_response": llm_text}

        except ValueError as e:
            if "does not exist" in str(e):
                return {"error": f"Vector DB collection '{collection_name}' not found. Please run the build script."}
            return {"error": f"An exception occurred: {str(e)}"}
        except Exception as e:
            return {"error": f"An unexpected exception occurred: {str(e)}"}

    async def _invoke_ollama(self, prompt):
        """Invokes the Ollama API to generate content."""
        url = f"{OLLAMA_BASE_URL}/api/generate"
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        def _post_request():
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()

        response_json = await asyncio.to_thread(_post_request)
        return response_json.get("response", "")

    def _create_llm_prompt(self, section, q_type, context_questions):
        """Constructs the prompt with instructions and context."""
        question_type_instruction = (
            "an MCQ (Multiple Choice Question) with 4 options labeled 'option1' to 'option4'" if q_type == 'mcq'
            else "a TITA (Type In The Answer) question where the answer is a numerical value or short text"
        )
        
        context_str = "\n---\n".join(context_questions)

        prompt = f"""
        You are an expert question setter for the CAT (Common Admission Test) exam.
        Your task is to generate a new, original question for the '{SECTION_FILENAME_MAP.get(section, section.upper())}' section.
        The question must be of type: {question_type_instruction}.
        It should be of a similar style, topic, and difficulty level to the following examples:
        ---
        {context_str}
        ---
        Your entire response MUST be a single, valid JSON object. Do not include any other text, markdown, or explanation.
        The JSON object must have the following structure:
        - For MCQ: {{"question_text": "...", "option1": "...", "option2": "...", "option3": "...", "option4": "...", "answer": "The correct option text", "explanation": "A brief explanation."}}
        - For TITA: {{"question_text": "...", "answer": "The numerical or short text answer", "explanation": "A brief explanation."}}
        """
        return prompt

    def _generate_cache_key(self, exam_name: str, stream: str | None = None, year: int | None = None):
        """Generate a cache key for exam lookup."""
        key_parts = [exam_name.upper()]
        if stream:
            key_parts.append(stream.upper())
        if year:
            key_parts.append(str(year))
        return "_".join(key_parts)

    def _find_cached_exam(self, exam_name: str, stream: str | None = None, year: int | None = None):
        """Check if a similar exam already exists in generated_questions folder."""
        try:
            exam_files = os.listdir(self.paths['generated_exams'])
            cache_key = self._generate_cache_key(exam_name, stream, year)
            
            # Look for files that match our pattern
            for file_name in exam_files:
                if file_name.startswith(f"{self.exam_type.lower()}_exam") and file_name.endswith(".json"):
                    # Load and check if it matches our requirements
                    file_path = os.path.join(self.paths['generated_exams'], file_name)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        exam_data = json.load(f)
                        
                    exam_details = exam_data.get('exam_details', {})
                    # Normalize both values, treating None and empty string as equivalent
                    cached_stream = (exam_details.get('stream') or '').upper()
                    requested_stream = (stream or '').upper()
                    
                    # For CAT, stream might be None, so we need to handle that case
                    if exam_details.get('name', '').upper() == exam_name.upper():
                        # If both streams are empty/None, or they match, it's a cache hit
                        if cached_stream == requested_stream:
                            if year and exam_details.get('year') == year:
                                print(f"Found cached exam: {file_name}")
                                return exam_data
                        
        except Exception as e:
            print(f"Error checking cached exams: {e}")
        
        return None

    async def generate_full_exam(self, exam_name: str, stream: str | None = None, year: int | None = None):
        """
        Orchestrates the generation of a full mock exam section by section
        to respect API rate limits. Checks for cached exams first.
        """
        # Check for cached exam first
        cached_exam = self._find_cached_exam(exam_name, stream, year)
        if cached_exam:
            print("Using cached exam - no AI generation needed!")
            return cached_exam
            
        print("No cached exam found, generating new exam with AI...")
        
        exam_name_upper = exam_name.upper()
        
        # Validate GATE stream if provided
        if exam_name_upper == "GATE":
            if not stream or stream.upper() not in GATE_STREAMS:
                return {"error": f"Invalid or missing GATE stream. Must be one of: {', '.join(GATE_STREAMS)}"}
        
        exam_structure = SUPPORTED_EXAMS.get(exam_name_upper)

        if not exam_structure:
            return {"error": f"Exam structure for '{exam_name_upper}' is not supported."}

        print(f"Generating {exam_name_upper} mock exam...")
        
        # Initialize exam structure based on exam type
        if exam_name_upper == "CAT":
            full_exam = {
                "exam_details": {"name": exam_name, "stream": stream, "year": year},
                "VARC": [], "DILR": [], "QA": [], "errors": []
            }
        else:  # GATE
            full_exam = {
                "exam_details": {"name": exam_name, "stream": stream, "year": year},
                "GA": [], "TECH": [], "errors": []
            }

        sections_to_process = list(exam_structure.keys())

        for i, section in enumerate(sections_to_process):
            print(f"\n--- Generating section: {section.upper()} ---")
            
            tasks = []
            structure = exam_structure[section]
            
            for q_type, count in structure.items():
                for _ in range(count):
                    tasks.append(self._generate_single_question(section, q_type, exam_name, stream, year))
            
            generated_questions = await asyncio.gather(*tasks)

            for q in generated_questions:
                section_key = q.get('section')
                if section_key and section_key in full_exam:
                    full_exam[section_key].append(q)
                elif "error" in q:
                    full_exam["errors"].append(q)
                else:
                    full_exam["errors"].append({"error": "Generated question has unknown section", "details": q})

            print(f"--- Section {section.upper()} generation complete. ---")

            if i < len(sections_to_process) - 1:
                print(f"Waiting for 1 seconds to avoid rate limiting...")
                await asyncio.sleep(1)
        
        print("\nFull exam generation complete.")
        self._save_exam(full_exam)
        return full_exam

    def _save_exam(self, exam_data):
        """Saves the generated exam to a timestamped JSON file."""
        try:
            os.makedirs(self.paths['generated_exams'], exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stream_suffix = f"_{exam_data['exam_details']['stream']}" if exam_data['exam_details'].get('stream') else ""
            file_name = f"{self.exam_type.lower()}_exam{stream_suffix}_{timestamp}.json"
            save_path = os.path.join(self.paths['generated_exams'], file_name)

            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(exam_data, f, indent=2)
            
            print(f"Successfully saved generated exam to: {save_path}")
        except Exception as e:
            print(f"Error saving the generated exam: {e}")

async def main_test():
    """For standalone testing of the RAG service."""
    # Test generating a standard CAT exam
    cat_service = RAGService("CAT")
    await cat_service.generate_full_exam(exam_name="CAT")
    
    # Test generating a GATE exam
    gate_service = RAGService("GATE")
    await gate_service.generate_full_exam(exam_name="GATE", stream="CS")

if __name__ == '__main__':
    asyncio.run(main_test())

