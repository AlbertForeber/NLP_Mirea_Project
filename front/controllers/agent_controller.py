import aiohttp
#tenacity - библиотека для повторных попыток выполнения функций при возникновении ошибок
from tenacity import retry, stop_after_attempt, wait_exponential
from aiogram.types import File
import io
import asyncio

class MlController:
    def __init__(self, base_url = "http://agent:8000", whisper = "http://stt:8002", tts="http://tts:8001"):
        self.whisper = whisper
        self.base_url = base_url
        self.tts_url = tts
        self.semaphore = asyncio.Semaphore(10)

    @retry(stop=stop_after_attempt(3), #остановитсья после 3 попыток
            wait=wait_exponential(multiplier=1,
                                   min=4, # min and max seconds to wait
                                     max=10)
                                     )
    #задержка = multiplier × 2^(попытка-1)
    async def get_note_thoughts(self, user_id: int, note_id: int):
        async with aiohttp.ClientSession() as session:
            try :
                async with session.get(
                    f"{self.base_url}/get-note-thoughts",
                    params={"user_id":user_id, "note_id":note_id},
                    timeout=aiohttp.ClientTimeout(total=30)

                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        #ЗАВИСИТ ОТ ТОГО, КАК ПРОПИСАНО В ДРУГОМ КОНТЕЙНЕРЕ
                        print("Agent Controller ", data)
                        return data
                    else:
                        raise Exception(f"Agent service error : {response.status}")
            except Exception as e:
                return "Сервис временно не доступен. Попробуйте позже"

    @retry(stop=stop_after_attempt(3),
           wait = wait_exponential(multiplier=1,
                                   min=4, max=10))
    async def delete_note(self, user_id:int, note_id: int):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.delete(
                    f"{self.base_url}/delete-note/",
                    params={"user_id": user_id, "note_id": note_id},
                    timeout= aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return True
                    else:
                        raise Exception(f"Agent service error : {response.status}")
            except Exception as e:
                raise Exception(f"Problem with aiohttp: ", str(e))

    @retry(stop=stop_after_attempt(3),
           wait = wait_exponential(multiplier=1,
                                   min=4, max=10))
    async def delete_thought(self, user_id: int, document_id: int, compound_id: int):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.delete(
                    f"{self.base_url}/delete-thought/",
                    params={"user_id":user_id, "document_id":document_id, "compound_id": compound_id},
                    timeout = aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                            return True
                    else:
                        raise Exception(f"Agent service error: {response.status}")
            except Exception as e:
                raise Exception (f"Problem with deleting thought ", str(e))


    @retry(stop=stop_after_attempt(3),
           wait = wait_exponential(multiplier=1,
                                   min=4, max=10))
    async def add_thoughts(self, user_id: int, note_id: int, speech: str):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/add-thoughts/",
                    params={"user_id":user_id, "note_id":note_id, "speech": speech},
                    timeout = aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                            return True
                    else:
                        raise Exception(f"Agent service error: {response.status}")
            except Exception as e:
                raise Exception (f"Problem with deleting thought ", str(e))





    @retry(stop=stop_after_attempt(3),
           wait = wait_exponential(multiplier=1,
                                   min=4, max=10))
    async def whisper_transcribation(self, audio_data) -> str:
        audio_data.seek(0)
        async with aiohttp.ClientSession() as session:
            form_data = aiohttp.FormData()
            form_data.add_field(
                'file',
                audio_data.read(),
                filename= "voice.ogg",
                content_type = 'audio/ogg'
            )

            async with session.post(
                f"{self.whisper}/upload-transcribe-audio/",
                data = form_data,
                timeout = aiohttp.ClientTimeout(total=60),
                headers={'Accept': 'application/json'}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print("Result", result)
                    return result["text"]
                else:
                    error = await response.text()
                    raise Exception(f"Whisper error: {error}")

    @retry(stop=stop_after_attempt(3),
           wait = wait_exponential(multiplier=1,
                                   min=4, max=10))
    async def _get_tts(self,  speech: str)-> tuple[bytes, str] | None:
        async with aiohttp.ClientSession() as session:
            json_ = {
                "text":speech,
                "speaker":"aidar",
                "sample_rate":48000
            }
            async with session.post(
                f"{self.tts_url}/synthesize",
                params = json_
            ) as response:
                if response.status == 200:

                    audio_bytes = await response.read()
                    return audio_bytes
                else:
                    error = await response.text()
                    raise Exception (f"TTS ERROR: {error}")

    async def  get_tts(self,  speech: str):
        async with self.semaphore:
            audio_bytes = await self._get_tts( speech)
            return audio_bytes


