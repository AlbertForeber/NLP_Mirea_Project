#DATABASE
#users - telegram_id, name
#categories - category_id,  name
#notes - note_id, user_id, name
#note_category - compund_id, note_id, category_id

#FAISS
#thoughts : metadata =  compound_id, label: str

#Settings
#есть базовые категории 3-5, которые могут быть у всех -> Note with id = 0
#



# ЕСТЬ ФАИС  для  каждого пользователя с его мыслями
# ЕСТЬ ОБЩИЙ ФАИСС со всеми категориями


#create new thought to note
#we get text from whisper -> text
# llm - extract thoughts -> list
# we go to faiss; get scores through существующие мысли
    # если выделилась мысль наиболее похожая, то получаем ее категорию  и добавляем в фаис + делаем compound------------------------

    #  not выдедилась - go to llm
    # получаем все категории из общего фаиса
    # LLM - передаем результата {катеогрию - оценка} и запрос: придумай новую категорию
    # проверяем созданную категорию через общий фаисс
        # выделилась набиолее похождая - слияние под найденную
        # не нашлось - добавляем новую категорию в общий раздел
    # databse -> добалвяем либо returned categories -> compound_id return  -> добавляем в пользовательский фаисс с метаданными


#create new thought to empty note
#we get text from whisper -> text
# llm - extract thoughts  + категории -> [category -> идея]
# проверяем созданную категорию через общий фаисс
        # выделилась набиолее похождая - слияние под найденную
        # не нашлось - добавляем новую категорию в общий раздел
# databse -> добалвяем либо returned categories -> compound_id return  -> добавляем в пользовательский фаисс с метаданными


#threshold - сравниваем схожесть ко всем существуюшим категориям

#prompt -> thoughts -> list; existing categories -> list; create new catgories

#-----------------------------------------------------------
#from db get categories from note_id=0 -> to



# create new thought for non empty node
#we get text from whisper
#we go to faiss; metada = note_id - to get existing thoughts and add them to prompt WITH DEFAULTS
#from db get categories from note_id=0 -> to

#--------------------------------------------------------------

#AGENT---------------------------------------------
#RAG
#----faiss
#get_or_create_user_store - получение фаисса пользователей 2    A
#create_user_store - создание фаисса пользователей 5            A
#unload_user_store - удаление по счетсчику из памяти 5          K
#get_category_store - подгрузим при инициализации 1             K
#async add_new_category - добавление категории в общий фаисс
#   -> возврашает категорию 4                                   A
#remove_thought - удаление мысли 2                              K
#remove_thoughts_by_user_id - удалени папки по user_id,         A
#   проверка на существование папки, проверка на выгрузку из памяти!
#get_thoughts_by_compund_id (список compund_id) - получение заметки 2   K
#add_thoughts - добавление змысли 1                             A
#get_category_for_thought - получение категориии для идеи ->
#   similarity_with_relevance = 0.7 и проверка score 5          K



#------llm
#split_into_thoughts    K
#generate_new_category  A


#POSTGRES------
#get_or_create_compund_id (note_id, category_id) 4  A
#get_or_create_category_id(category_name)        4  K
#get_compound_id(note_id, category_name) -> обобщающая для get_ compound_id, category_id 1  K
#get_note_compound(note_id) -> list[Compound_id] 2  A

#Пример запроса от дипсика
# WITH attempt_insert AS (
#     INSERT INTO items (field1, field2)
#     VALUES ($1, $2)
#     ON CONFLICT (field1, field2) DO NOTHING
#     RETURNING id
# )
# SELECT id FROM attempt_insert
# UNION
# SELECT id FROM items
# WHERE field1 = $1 AND field2 = $2
# LIMIT 1


#----------Communication------------------------------
#private-------------------
#get_new_category                       K
    #-> generate_new_category
    #-> add_new_category - проверка на слияние
    # возрат новой, либо созданной



#----------API-------------
#add_thoughts (user_id, note_id, ) 5    A
    # get_or_create_user_store
    # split_into_thoughts
    # get_category_for_thought -> для каждой -> categroy_name bиз существующих либо None
        #для пустой get_new_category -> получаем category_name новую

    #из postgres get_compound_id -> compound_id
    #добавляем мысли из фаисса add_thoughts формирует для добавления add_documents(list[Document]) -> None
    #

#get_note_thoughts(user_id, note_id) 4  K
    # get_or_create_user_store
    # from postgres get get_note_compounds
    # from faiss  get_thoughts_by_compund_id
    # -> {"category": [{content: Document.page_content, id: Document.id}]}   [(category, [{content:, id:}]),(),()]

#delete_thought(user_id, document_id(самого класса Document)) 2 A
    #get_or_create_user_store
    #из фаисса remove_thought

#delete_user(user_id): 1            K
    #remove_thoughts_by_user_id

#delete_note(user_id, note_id): 2   K
    #from postgres get_note_compound(note_id) -> compounds
    #remove_by_compund from faiss -> many
