from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import List, Optional, List
from langchain_core.prompts import PromptTemplate, FewShotPromptTemplate

import os, asyncio, time

LLM_SEMAPHORE = asyncio.Semaphore(3)

class OutputForCategory(BaseModel):
    category: str = Field(description="Category for current thought", max_length=50)

class OutputForSplittedThoughts(BaseModel):
    thoughts: List[str] = Field(description="List of selected thoughts. It consists of only thoughts that you find in user's prompt")

#"http://localhost:11434/v1"
class LLMModule:
    def __init__(self) -> None:
        # base_url = os.getenv("BASE_URL", "") + "/v1"
        base_url="http://77.83.85.58:11435"+ "/v1"

        self.llm = ChatOpenAI(
            base_url=base_url,
            api_key="no_key_required",
            model="gemma3:4b",
            temperature=0,
        )

    async def split_into_thoughts(self, text: str) -> Optional[list]:
        eng_system_prompt = "You are a helpful assistant who can find ideas, plans and thoughts in the given text." \
        "Text itself is not scientific, but is a transcribed real human speech, so in one text many thoughts can occur which are not related to each other." \
        "You need to find all of them and return a list consisted of them. " \
            "Thoughts can be seperated by comma, point or even by nothing." \
        "Different, unrelated  thoughts can be connected via syntactic link with verb, noun,  adjective and any other." \
        "Examples will be given in Russian language." \
        "Пример первый : хочу сходить в зал, почитать книгу - это две задачи: 1) сходить в зал 2) почитать книгу." \
    "Второй пример: нужно приготовить еду и написать рапорт - это две задачи: 1) приготовить еду 2) написать рапорт." \
    "Выведи список пронумерованным. Пример: 1) сходить в зал 2) почитать книгу"

        system_prompt = "Ты полезный помощник, который находит в полученном тексте идеи, планы, мысли." \
    "Сам текст не является научным, а транскрибированной живой речью человека, поэтому в одном тексте может быть много различных мыслей, несвязанных друг с другом." \
    "Тебе нужно будет найти каждую из них и вернуть список найденных." \
    "Мысли могут быть разделены запятой, или точкой, или даже не чем. " \
    "Разные мысли  могут быть синтаксически  связаны от одного глагола, существительного, прилагательного и других частей речи." \
    "Пример первый : хочу сходить в зал, почитать книгу - это две задачи: 1) сходить в зал 2) почитать книгу." \
    "Второй пример: нужно приготовить еду и написать рапорт - это две задачи: 1) приготовить еду 2) написать рапорт." \
    "Выведи список пронумерованным. Пример: 1) сходить в зал 2) почитать книгу"

        system_query = "Ты профессиональный организатор планов и идей" \
    "Извлеки из входного текста все планы и идеи, игнорируя лишние конструкции, междометия, второстепенные части речи и эмоции." \
    "На вход ты получаешь транскрибированную человеческую речь, которая может состоять из множества мыслей." \
    "Выдели каждую идею или план отдельно, даже если несколько планов или идей связаны по тематике или грамматически. Ориентируйся на количество сказуемых" \
    "Для более точного ответа опирайся на следующие примеры:" \
    "Пример #1: " \
    "Ввод: пора бы постирать вещи и еще приготовить еду на завтра." \
    "Вывод: 1) постирать вещи 2) приготовить еду;" \
    "Пример #2:" \
    "Ввод: надо встретиться с Вадимом и хочу убраться в комнате." \
    "Вывод: 1) встретиться с Вадимом 2) убраться в комнате" \
    "Пример #3:" \
    "Ввод: хочу прикупить пальто" \
    "Вывод: 1) купить пальто"

        model = self.llm.with_structured_output(OutputForSplittedThoughts)
        async with LLM_SEMAPHORE:
            try:
                result = await asyncio.wait_for(model.ainvoke([
                    {"role":"system", "content":system_query},
                    {"role":"user", "content":text}
                ]), timeout=180)
                return result.thoughts
            except asyncio.TimeoutError:
                print("Timeout")



    async def get_gnc_system_prompt(self) -> FewShotPromptTemplate:
        examples = [
              {"thought": "Убраться в комнате", "category" : "Уборка"},
              {"thought": "Сходить за продуктами", "category" : "Покупки"},
              {"thought": "Встретиться с Вовой", "category" : "Встречи"},
              {"thought" : "Написать код", "category" : "Рабочие задачи"},
              {"thought" : "Написать картину", "category" : "Идеи"}
         ]

        example_template = """
Input: {thought}
Output: {category}
"""
        example_prompt = PromptTemplate(
             input_variables=["thought", "category"],
             template=example_template
        )

        final_prompt = FewShotPromptTemplate(
            examples=examples,
            example_prompt=example_prompt,
            prefix="You are helpful assistant, who transforms thoughts into categories. You should not make it to specific, keep it wide enough. Output MUST contain only one category of ONE or TWO words. " \
            "Your output must contain less than 50 characters. You have to provide categories in Russian language, there're some examples in this language. You have to create your own category, don't pick from example ones:",
            example_separator="\n\n",
            suffix="Input: {thought}\nOutput:",
            input_variables=["thought"]
        )

        return final_prompt

    async def generate_new_category(self, query: str) -> str:
        prompt = await self.get_gnc_system_prompt()
        formatted_prompt = prompt.format(thought=query)

        messages = [
             {"role" : "system", "content" : formatted_prompt}
        ]

        model = self.llm.with_structured_output(OutputForCategory)


        async with LLM_SEMAPHORE:
            return (await model.ainvoke(messages)).category


async def test():
    llm = LLMModule()

    start = time.time()
    a = await asyncio.gather(llm.generate_new_category("Сходить к другу"), llm.generate_new_category("Сходить к друзьям"), llm.generate_new_category("Купить книгу"))
    print("Thought for", time.time() - start, "secs")
    return a

if __name__ == "__main__":
    print(asyncio.run(test()))
