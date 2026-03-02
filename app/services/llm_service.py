from groq import Groq
from fastapi.concurrency import run_in_threadpool
from app.core.config import settings

GROQ_MODEL = settings.groq_model
client = Groq(api_key=settings.groq_api_key)


def build_prompt(question: str, context: str) -> list:
    system_prompt = (
        "You are a strict RAG assistant.\n"
        "Answer ONLY using the provided context.\n"
        "If the answer is not in the context, say: "
        "'I cannot find this information in the provided documents.'\n"
        "Do not use external knowledge."
    )

    user_prompt = f"""
Context:
{context}

Question:
{question}
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def generate_answer(question: str, context: str) -> str:
    messages = build_prompt(question, context)

    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=1024,
        )
    except Exception as e:
        raise RuntimeError(f"Groq API Error: {e}") from e

    return completion.choices[0].message.content.strip()

async def generate_answer_async(question: str, context: str) -> str:
    return await run_in_threadpool(
        lambda: generate_answer(question, context)
    )