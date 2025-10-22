from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
import hashlib

app = FastAPI(title="String Analyzer API - FIK001")

# In-memory database
database = {}

# ====== MODELS ======
class StringRequest(BaseModel):
    value: str

# ====== UTILITIES ======
def analyze_string(value: str):
    """Analyze a string and return its computed properties."""
    cleaned = value.strip()
    is_palindrome = cleaned.lower() == cleaned[::-1].lower()
    unique_characters = len(set(cleaned))
    word_count = len(cleaned.split())
    sha256_hash = hashlib.sha256(cleaned.encode()).hexdigest()

    # Frequency map
    freq_map = {}
    for char in cleaned:
        freq_map[char] = freq_map.get(char, 0) + 1

    return {
        "length": len(cleaned),
        "is_palindrome": is_palindrome,
        "unique_characters": unique_characters,
        "word_count": word_count,
        "sha256_hash": sha256_hash,
        "character_frequency_map": freq_map,
    }

# ====== ROUTES ======
@app.post("/strings", status_code=201)
def create_string(request: StringRequest):
    if not request.value or not isinstance(request.value, str):
        raise HTTPException(status_code=400, detail="Invalid or missing 'value' field")

    analyzed = analyze_string(request.value)
    sha_hash = analyzed["sha256_hash"]

    if sha_hash in database:
        raise HTTPException(status_code=409, detail="String already exists in the system")

    entry = {
        "id": sha_hash,
        "value": request.value,
        "properties": analyzed,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    database[sha_hash] = entry
    return entry

@app.get("/strings/{string_value}")
def get_string(string_value: str):
    """Fetch a specific string analysis by value."""
    sha_hash = hashlib.sha256(string_value.strip().encode()).hexdigest()
    if sha_hash not in database:
        raise HTTPException(status_code=404, detail="String not found")
    return database[sha_hash]

@app.get("/strings")
def list_strings(
    is_palindrome: bool | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    word_count: int | None = None,
    contains_character: str | None = None,
):
    """List all strings with filtering options."""
    results = list(database.values())

    # Apply filters
    if is_palindrome is not None:
        results = [r for r in results if r["properties"]["is_palindrome"] == is_palindrome]
    if min_length is not None:
        results = [r for r in results if r["properties"]["length"] >= min_length]
    if max_length is not None:
        results = [r for r in results if r["properties"]["length"] <= max_length]
    if word_count is not None:
        results = [r for r in results if r["properties"]["word_count"] == word_count]
    if contains_character is not None:
        results = [r for r in results if contains_character in r["value"]]

    return {
        "data": results,
        "count": len(results),
        "filters_applied": {
            "is_palindrome": is_palindrome,
            "min_length": min_length,
            "max_length": max_length,
            "word_count": word_count,
            "contains_character": contains_character,
        },
    }

@app.get("/strings/filter-by-natural-language")
def filter_by_natural_language(query: str = Query(..., description="Natural language query")):
    """Very simple natural language filter parser."""
    query_lower = query.lower()
    parsed_filters = {}

    if "palindromic" in query_lower:
        parsed_filters["is_palindrome"] = True
    if "longer than" in query_lower:
        try:
            num = int(query_lower.split("longer than")[1].split()[0])
            parsed_filters["min_length"] = num + 1
        except Exception:
            raise HTTPException(status_code=400, detail="Unable to parse number in query")
    if "single word" in query_lower:
        parsed_filters["word_count"] = 1
    if "contain" in query_lower:
        try:
            letter = query_lower.split("contain")[1].strip().split()[0][0]
            parsed_filters["contains_character"] = letter
        except Exception:
            raise HTTPException(status_code=400, detail="Unable to parse contained character")

    if not parsed_filters:
        raise HTTPException(status_code=400, detail="Unable to parse natural language query")

    # Apply filters and safely add interpreted_query
    results = list_strings(**parsed_filters)
    results["interpreted_query"] = {
        "original": query,
        "parsed_filters": parsed_filters,
    }
    return results

@app.delete("/strings/{string_value}", status_code=204)
def delete_string(string_value: str):
    """Delete a string by its value."""
    sha_hash = hashlib.sha256(string_value.strip().encode()).hexdigest()
    if sha_hash not in database:
        raise HTTPException(status_code=404, detail="String not found")
    del database[sha_hash]
    return None

@app.get("/")
def root():
    return {"message": "Welcome FIK001 - String Analyzer API running successfully 🚀"}
