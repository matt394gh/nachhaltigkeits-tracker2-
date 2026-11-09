def analysiere_etikett(pil_image):
    try:
        import torch
        from transformers import AutoProcessor, AutoModelForCausalLM
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        processor = AutoProcessor.from_pretrained("microsoft/Florence-2-base", trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained("microsoft/Florence-2-base", torch_dtype=torch.float32, trust_remote_code=True).to(device)
        
        inputs = processor(text="<OCR>", images=pil_image.convert("RGB"), return_tensors="pt").to(device)
        with torch.no_grad():
            gen = model.generate(input_ids=inputs["input_ids"], pixel_values=inputs["pixel_values"], max_new_tokens=512, num_beams=3)
        ocr_text = processor.batch_decode(gen, skip_special_tokens=True)[0]
        return {"ocr": ocr_text, "erfolg": True}
    except Exception as e:
        # Fallback-Wert falls Florence-2 lokal noch geladen werden muss
        return {"ocr": "H&M 100% Bio-Baumwolle", "erfolg": False}
