import os
import fitz  # PyMuPDF
from werkzeug.datastructures import FileStorage
import tempfile


def load_file_content(file_input) -> str:
    """
    อ่านเนื้อหาจากไฟล์ .txt หรือ .pdf แล้วรวมเป็นข้อความเดียว
    ใช้ PyMuPDF (fitz) สำหรับ PDF เพื่อความเร็วและความแม่นยำ
    รองรับทั้ง file path (str) และ FileStorage object จาก Flask
    """
    
    # Handle Flask FileStorage object
    if isinstance(file_input, FileStorage):
        filename = file_input.filename
        if not filename:
            raise ValueError("ไม่พบชื่อไฟล์")
            
        ext = os.path.splitext(filename)[1].lower()
        
        # ✅ สำหรับไฟล์ข้อความทั่วไป
        if ext == ".txt":
            content = file_input.read().decode('utf-8', errors='ignore')
            file_input.seek(0)  # Reset file pointer
            return content
            
        # ✅ สำหรับไฟล์ PDF
        elif ext == ".pdf":
            # Save to temporary file for PyMuPDF processing
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                file_input.save(temp_file.name)
                file_input.seek(0)  # Reset file pointer
                
                try:
                    text_pages = []
                    with fitz.open(temp_file.name) as doc:
                        for page in doc:
                            text = page.get_text("text")
                            text_pages.append(text.strip())
                    return "\n".join(text_pages)
                except Exception as e:
                    raise ValueError(f"ไม่สามารถอ่าน PDF ได้: {e}")
                finally:
                    # Clean up temporary file
                    os.unlink(temp_file.name)
                    
        else:
            raise ValueError(f"ไม่รองรับไฟล์ประเภท {ext}")
    
    # Handle file path string (original functionality)
    elif isinstance(file_input, str):
        file_path = file_input
        ext = os.path.splitext(file_path)[1].lower()

        # ✅ สำหรับไฟล์ข้อความทั่วไป
        if ext == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        # ✅ สำหรับไฟล์ PDF
        elif ext == ".pdf":
            text_pages = []
            try:
                with fitz.open(file_path) as doc:
                    for page in doc:
                        text = page.get_text("text")  # ดึงข้อความแบบ text mode
                        text_pages.append(text.strip())
                return "\n".join(text_pages)
            except Exception as e:
                raise ValueError(f"ไม่สามารถอ่าน PDF ได้: {e}")

        else:
            raise ValueError(f"ไม่รองรับไฟล์ประเภท {ext}")
    
    else:
        raise ValueError("ต้องระบุ file path (str) หรือ FileStorage object")
