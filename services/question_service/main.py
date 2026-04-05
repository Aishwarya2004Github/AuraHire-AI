from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.post("/generate_questions")
async def generate_questions(request: Request):
    try:
        # Request se JSON data nikalna
        data = await request.json()
        
        skills = data.get('skills', [])
        jd_text = data.get('jd_text', '')

        # AI Logic: Questions generate karna
        questions = []
        if skills:
            for skill in skills[:3]: # Top 3 skills ke liye
                questions.append(f"Explain your experience with {skill} in a real-world project.")
        
        # Fallback questions agar data kam ho
        if len(questions) < 3:
            questions.extend([
                "How do you handle debugging in complex systems?",
                "Tell me about a time you optimized a piece of code.",
                "What is your approach to learning new frameworks?"
            ])

        return {
            "questions": questions[:5] # Max 5 questions bhejna
        }

    except Exception as e:
        return JSONResponse(
            status_code=422,
            content={"error": f"Invalid Data: {str(e)}", "questions": []}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8004)