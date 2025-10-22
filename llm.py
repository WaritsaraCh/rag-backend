import ollama
import time
import requests
from bs4 import BeautifulSoup

def is_iphone_query(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in ["iphone", "ไอโฟน"])  # basic detection for EN/TH

def fetch_apple_iphone_info(timeout: int = 6) -> str | None:
    try:
        url = "https://www.apple.com/th/iphone/"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0 Safari/537.36",
            "Accept-Language": "th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # Prefer text in <main> content area
        tags = soup.select("main h1, main h2, main h3, main p, main li")
        lines = []
        seen = set()
        for tag in tags:
            txt = tag.get_text(strip=True)
            if not txt or txt in seen:
                continue
            seen.add(txt)
            # Prioritize lines mentioning iPhone; keep some general lines for context
            if ("iphone" in txt.lower()) or ("ไอโฟน" in txt.lower()) or len(lines) < 30:
                lines.append(txt)
            if len(" ".join(lines)) > 1400:
                break
        if not lines:
            return None
        summary = "\n".join(lines[:80])
        return f"ข้อมูลทางการจาก Apple ประเทศไทย:\n{summary}\nแหล่งที่มา: https://www.apple.com/th/iphone/"
    except Exception as e:
        print(f"⚠️ Apple fetch error: {e}")
        return None

def generate_answer(query, context_docs, history_messages):
    # รวม context จากเอกสาร
    context_text = "\n".join([doc["chunk_text"] for doc in context_docs]) if context_docs else "No context available."

    # If question is about iPhone, fetch official info from Apple Thailand and prepend
    if is_iphone_query(query):
        apple_info = fetch_apple_iphone_info()
        if apple_info:
            context_text = f"{apple_info}\n\n{context_text}" if context_text else apple_info

    # Truncate context if too long to prevent memory issues
    max_context_length = 1500  # Limit context to prevent memory overflow
    if len(context_text) > max_context_length:
        context_text = context_text[:max_context_length] + "..."

    system_prompt = f"""
        You are a system assistant that knows this system well and answers questions in a formal, clear, accurate, and polite manner.
        Always base your answer only on the given context, conversation history, and trusted external data sources as appropriate.
        If the context and history do not contain enough information, perform a web search or data fetch as described below before answering concisely.

        Context:
        {context_text}

        Calculation Rules:
        - If the user asks to calculate, estimate, compare numerical values, or derive results from formulas, you must use the TOOL `calculator` to perform the calculation accurately.
        - Clearly show important numeric results or comparisons in your final answer.
        - If the user’s question mixes reasoning and calculation, first reason conceptually, then use the calculator for numeric steps.
        - Example triggers include: “calculate”, “compare”, “find total”, “percentage”, “difference”, “average”, “cost”, “duration”, “estimate”, or any arithmetic expression (e.g., 120*1.07).

        Answer Format:
        - If the answer is long, present it as a numbered list (1., 2., 3.).
        - If the answer is short, reply in a single polite sentence without numbering.
        - When token length is limited, summarize the most essential information first.
        - Always respond in the same language as the question.
        """


    # เตรียม messages สำหรับ LLM - limit history to prevent memory issues
    messages = [{"role": "system", "content": system_prompt}]
    if history_messages:
        # Limit history to last 3 messages to save memory
        recent_history = history_messages[-2:] if len(history_messages) > 3 else history_messages
        for m in recent_history:
            if "role" in m and "content" in m:
                messages.append(m)

    messages.append({"role": "user", "content": query})

    try:
        # Add retry mechanism for Ollama stability
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = ollama.chat(
                    model="llama3.2:latest",
                    messages=messages,
                    options={
                        "temperature": 0.1,
                        "num_ctx": 1024,  
                        "num_predict": 256, 
                        "top_k": 10,
                        "top_p": 0.9,
                        "repeat_penalty": 1.1
                    }
                )
                break  # Success, exit retry loop
            except Exception as retry_error:
                print(f"❌ Ollama attempt {attempt + 1} failed: {retry_error}")
                if attempt == max_retries - 1:
                    raise retry_error
                time.sleep(1)  # Wait before retry

        answer = response.get("message", {}).get("content", "")
        if not answer:
            answer = "ขออภัย ฉันไม่พบคำตอบที่ชัดเจนจากข้อมูลที่มีค่ะ"

        return answer.strip()

    except Exception as e:
        print(f"❌ Error in generate_answer: {e}")
        return "เกิดข้อผิดพลาดในการประมวลผลคำตอบค่ะ"
