import ollama
import time  
         
def generate_answer(query, context_docs, history_messages):
    # รวม context จากเอกสาร
    context_text = "\n".join([doc["chunk_text"] for doc in context_docs]) if context_docs else "No context available."

    print(context_text)
    # Truncate context if too long to prevent memory issues
    max_context_length = 5000  # Increase context allowance to reduce truncation
    # if len(context_text) > max_context_length:
    #     context_text = context_text[:max_context_length] + "..."


    system_prompt = f"""
        You are a knowledgeable and analytical system assistant who understands this system thoroughly. 
        Your task is to analyze, summarize, and accurately answer user questions based strictly on the provided information.

        Guidelines:
        1. Base every answer **only** on the given context (`{context_text}`), conversation history, or explicitly provided data.
        2. **Do not** invent or assume information that is not in the context.
        3. Perform analysis or reasoning if needed to form a clear and insightful conclusion.
        4. When summarizing, focus on the **main ideas**, **key findings**, and **practical implications**.
        5. Maintain a **formal, clear, accurate, and polite** tone at all times.
        6. If the question requires interpretation, clearly explain the reasoning behind your answer.

        Answer Format:
        - Always reply in the **same language** as the question.
        - If the answer is short → reply in one concise and polite sentence.
        - If the answer is longer → use a **numbered list** or clear bullet points for readability.
        - If the question cannot be answered from the context → politely state that the information is not available.
        - When token length is limited → summarize the **core analysis first**, then optional details.

        Goal:
        Provide an accurate, well-reasoned, and contextually grounded answer that helps the user fully understand the topic.
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
                        "num_ctx": 2048,  
                        "num_predict": 512, 
                        "top_k": 10,
                        "top_p": 0.9,
                        "repeat_penalty": 1.1,
                    },
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
