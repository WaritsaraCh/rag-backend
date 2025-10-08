import ollama
import time

def generate_answer(query, context_docs, history_messages):
    # รวม context จากเอกสาร
    context_text = "\n".join([doc["chunk_text"] for doc in context_docs]) if context_docs else "No context available."

    # Truncate context if too long to prevent memory issues
    max_context_length = 1500  # Limit context to prevent memory overflow
    if len(context_text) > max_context_length:
        context_text = context_text[:max_context_length] + "..."

    system_prompt = f"""
        You are a system assistant that knows this system well and answers questions in a formal, clear, accurate, and polite manner.
        Always base your answer only on the given context and conversation history appropriately.
        If the context and history do not contain enough information, please provide a concise summary instead.

        Context:
        {context_text}

        Answer:
        - If the answer is long, provide it in a numbered list format (1., 2., 3.).
        - If the answer is short, reply in a single polite sentence without numbering.
        - If token length is limited, summarize the most essential information first.
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
                        "num_ctx": 1024,  # Further reduce context window
                        "num_predict": 256,  # Reduce response length
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
