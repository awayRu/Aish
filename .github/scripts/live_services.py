from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys
import threading


sys.path.insert(0, str(Path.cwd()))
os.environ["KIVY_NO_ARGS"] = "1"
with TemporaryDirectory() as folder:
    os.environ["AISH_DATA_DIR"] = folder
    from PIL import Image, ImageDraw
    import main

    file = Path(folder) / "shapes.jpg"
    test = Image.new("RGB", (256, 128), "white")
    pen = ImageDraw.Draw(test)
    pen.rectangle((16, 16, 104, 112), fill="red")
    pen.ellipse((149, 16, 237, 112), fill="blue")
    test.save(file)

    def text_check():
        models = main._provider_list()
        text, error = main.ask_ai(
            [{"role": "user", "content": "Сколько будет 16 плюс 7? Ответь одним числом."}],
            cancel_event=threading.Event(), providers=models)
        print("Текст:", text or error, flush=True)
        return bool(text and "23" in text)

    def vision_check():
        media = main.vision_content("Назови буквально цвет и форму каждого объекта.", str(file))
        text, error = main.ask_ai([{"role": "user", "content": media}],
                                  cancel_event=threading.Event(), providers=(main.VISION_PROVIDER,))
        print("Фото:", text or error, flush=True)
        return bool(text and "красн" in text.casefold() and ("син" in text.casefold() or "голуб" in text.casefold()))

    with ThreadPoolExecutor(max_workers=2) as pool:
        text_future, vision_future = pool.submit(text_check), pool.submit(vision_check)
        checks = (text_future.result(), vision_future.result())
    main.DB.close()
    if not all(checks):
        raise SystemExit(1)
