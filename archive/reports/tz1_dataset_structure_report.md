# ТЗ №1 — Разведка источников данных

**Дата:** 2026-05-04
**Репозиторий:** MAS_datasets_research

## Резюме

| Датасет | HF ID | Записей | Типизация ошибок | Что можно извлечь |
|---------|-------|---------|------------------|-------------------|
| Who&When | Kevin355/Who_and_When | ~184 | ✅ Да | `mistake_reason` (free-text, 182 уник.), `mistake_agent`, `mistake_step` |
| AgentRx | microsoft/AgentRx | 159 (73 аннот.) | ✅ Частично | `failure_category` (8+ типов), `failed_agent`, `step_number` |
| nebius/SWE-agent | nebius/SWE-agent-trajectories | ~80 036 | ❌ Нет | `exit_status` (3 кат.), длина траектории |
| SWE-Gym/OpenHands | SWE-Gym/OpenHands-Sampled-Trajectories | ~6 055 | ❌ Нет | `resolved` (bool), длина траектории |
| Terminalbench | yoonholee/terminalbench-trajectories | ~52 104 | ❌ Нет | `reward` (binary), `duration_seconds` |
| ITBench | ibm-research/ITBench-Trajectories | 105 | ⚠️ Частично | `type:error` (operational, нет таксономии) |
| Mind2Web-Live | iMeanAI/Mind2Web-Live | ~500 | ❌ Нет | Только описания задач, траектории отсутствуют |

## 1. Существующая таксономия ошибок

Источник: `fault_mode_analysis_and_classification_ru.html`

### 1.1 TRAIL — таблица ошибок

| Класс ошибок | Подгруппа | Категория | Последствия | Моделир. |
|-------------|-----------|-----------|-------------|----------|
| 1 | Потеря локального KV-cache после ребута модуля | Context Handling Failures | Прямое совпадение по эффекту: потеря состояния или контекста | потеря состояния/контекста, неверное продолжение или повтор  | (2) |
| 2 | Деградация оборудования на длинном горизонте | Timeout Issues; Resource Exhaustion; Service Errors | Причина производительности, которая проявляется как задержка | рост latency, очереди, service failure и ретраи. | (4) |
| 3 | Троттлинг GPU и падение частот | Timeout Issues; Resource Exhaustion | Замедление исполнения приводит к просадке throughput, росту  | просадка throughput, рост очередей и таймаутов. | (4) (Не будем, но есть исследование на эту тему; требуются д |
| 4 | Коррелированные сбои SSD | Resource Not Found; Service Errors; Timeout Issues | Инфраструктурная причина, наблюдаемая как недоступность данн | недоступность данных/сервиса, fail или retry | (4) |
| 5 | Сетевые и power-сбои выше уровня вычислительного модуля | Service Errors; Timeout Issues; Resource Not Found | Коррелированный отказ инфраструктуры, а не ошибка рассуждени | коррелированная недоступность узлов/сервиса, каскад ретраев | (4) |
| 6 | Bottleneck по memory bandwidth при KV-heavy inference | Timeout Issues; Resource Exhaustion; Resource Abuse | Узкое место снижает throughput и может провоцировать ретраи. | падение throughput, очереди, retry amplification/resource ab | (2) |
| 7 | Retry policy: backoff, multiplier, max_backoff, jitter | Resource Abuse; Timeout Issues; Task Orchestration | Это recovery-политика; плохая настройка может создать retry  | лишние циклы, retry storm, задержка. | (2) |
| 10 | Нагрузочно-зависимый slowdown_mult | Timeout Issues; Resource Exhaustion | Модель производительности, меняющая вероятность задержек и о | нагрузочно-зависимое замедление, таймауты, рост очередей | Resource Exhaustion (1); Timeout Issues (2) |
| 12 | Роль ноды задается regex; prefill-блоки не представлены | Environment Setup Errors; Tool Definition Issues; Task Orche | Риск конфигурации и моделирования графа исполнения. | неверная роль узла/неполный граф меняет маршрут и расчёт эфф | (2), но это не fault mode системы, а ограничение/дефект само |
| 13 | KV-transfer: потеря или повреждение state | Context Handling Failures | Сбой state-transfer может сломать продолжение, память или це | потеря/повреждение state-transfer ломает продолжение decode | (2) |


## 2. Who&When — Детальный анализ

**Всего записей:** 184  (Algorithm-Generated: 126, Hand-Crafted: 58)

### 2.1 Схема (Algorithm-Generated)

| Поле | Тип |
|------|------|
| `mistake_agent` | `object` |
| `mistake_reason` | `object` |
| `question_ID` | `object` |
| `is_corrected` | `bool` |
| `question` | `object` |
| `history` | `object` |
| `mistake_step` | `object` |
| `groundtruth` | `object` |

### 2.2 Распределение is_correct

is_corrected
False    184

### 2.3 Частоты: mistake_agent (топ-15)

| Агент | Кол-во |
|------|------|
| `WebSurfer` | 31 |
| `Verification_Expert` | 18 |
| `Orchestrator` | 18 |
| `PythonDebugging_Expert` | 7 |
| `DataAnalysis_Expert` | 6 |
| `DataVerification_Expert` | 5 |
| `Validation_Expert` | 5 |
| `WebServing_Expert` | 4 |
| `Assistant` | 4 |
| `FileSurfer` | 3 |
| `VideoContentAnalysis_Expert` | 2 |
| `Research_Expert` | 2 |
| `DataExtraction_Expert` | 2 |
| `Statistics_Expert` | 2 |
| `Websurfer` | 2 |

### 2.4 Все уникальные mistake_reason

**Всего уникальных:** 181 (из 184 non-null)

**Повторяющиеся mistake_reason:**

- (2x) `The code is incorrect for the task.`
- (2x) `The expert wrote code with bugs multiple times, leading to the exhaustion of the step limits.`
- (2x) `The code is wrong.`

**Частотная таблица (все значения):**

| mistake_reason | Кол-во |
|------|------|
| `The code is incorrect for the task.` | 2 |
| `The expert wrote code with bugs multiple times, leading to the exhaustion of the step limits.` | 2 |
| `The code is wrong.` | 2 |
| `WebSurfer's inability to reliably access the requested documents resulted in the overall task failure, as the necessary ` | 1 |
| `The task description is not well aligned with the question, causing the subsequent steps to deviate from the correct dir` | 1 |
| `The expert incorrectly identified BaseBagging as the predictor base command that received a bug fix, when, according to ` | 1 |
| `The Movie_Expert provides an incorrect list of Daniel Craig movies with a duration of less than 150 minutes. The expert ` | 1 |
| `The code is incorrect because it does not import the necessary Python packages.` | 1 |
| `The code provided by MerriamWebsterWordOfTheDay_Historian_Expert is incorrect. Executing the code did not return the cor` | 1 |
| `The expert provided incorrect text in the in-line citation, leading to an error in the comparison. The correct word in t` | 1 |
| `The calculation incorrectly assumes that Bob's guesses will always match the number of coins in each box, guaranteeing m` | 1 |
| `The agent should review the page history of the Wikipedia article to obtain the information. Instead, it initiated a sea` | 1 |
| `The agent fails to collect price data for the daily tickets and season passes for California's Great America in 2024.` | 1 |
| `The DataAnalysis_Expert generates data to answer the user's question, which is not the correct approach to solving the p` | 1 |
| `WebSurfer misinterpreted or failed to retrieve the correct Latin root, leading to confusion in identifying the related S` | 1 |
| `The Orchestrator should let the Websurfer scroll down to check more movies. Moreover, there are search filters for keywo` | 1 |
| `WebSurfer's query is not concise enough to retrieve complete information to answer the original question, which leads to` | 1 |
| `The agent does not verify the information and check whether the highest price of the house is located at Mission Bay. Th` | 1 |
| `The WebSurfer directly reaches a conclusion without performing the correct actions, such as taking a screenshot and extr` | 1 |
| `The page retrieved by WebSurfer does not provide relevant information to address the question, causing the Orchestrator ` | 1 |
| `WebSurfer did not retrieve a list of eateries near Harkness Memorial State Park sorted by distance and operating hours. ` | 1 |
| `WebSurfer makes two mistakes in this step, leading to failure. 1. It does not include the '2+ bathrooms' criterion in th` | 1 |
| `The key word should include Monterey Bay Aquarium website.` | 1 |
| `The Orchestrator should instruct WebSurfer to collect the full list of Daniel Craig's movies on IMDb. Instead, it only d` | 1 |
| `GIS_DataAnalysis_Expert did not directly access the USGS database to verify the ZIP codes. The expert should have indepe` | 1 |
| `The Orchestrator writes incorrect code.` | 1 |
| `The agent wrote incorrect code and obtained the wrong result.` | 1 |
| `The Tickets_Pricing_Expert provides incorrect ticket prices. The expert should take the necessary steps to obtain accura` | 1 |
| `The agent begins providing the full text of the poem without retrieving the text and formatting from websites.` | 1 |
| `The assistant provides an incorrect plan in response to an incorrect question.` | 1 |
| `The agent provide the wrong name of the actor` | 1 |
| `The price provided by HawaiiRealEstate_Expert is incorrect, causing the error to propagate through subsequent steps to t` | 1 |
| `The experts incorrectly present the problems.` | 1 |
| `The code provided by WaybackMachine_Expert is not reasonable.` | 1 |
| `The code provided by the Debugging_Expert is incorrect and unrelated to the task.` | 1 |
| `The expert didn't import the necessary tables, leading to the exhaustion of the step limits.` | 1 |
| `The WebServing_Expert failed to retrieve useful information from the paper link.` | 1 |
| `The agent is approaching the task in the wrong direction. It failed to locate the restaurant's name.` | 1 |
| `To solve this problem, a web search approach should be used, as there are no attached files for this task. The error occ` | 1 |
| `The answer provided by Verification_Expert was incorrect.` | 1 |
| `The DFS algorithm is not correctly exploring the possible words on the Boggle board.` | 1 |
| `The answer provided by Clinical_Trial_Data_Analysis_Expert was incorrect.` | 1 |
| `The expert should not suggest manual inspection. Instead, they should use relevant tools or methods to extract the requi` | 1 |
| `The Vegan_Food_Expert provides information directly without taking the necessary actions, resulting in incorrect informa` | 1 |
| `The code provided by WikipediaHistory_Expert is incorrect and does not return any useful results.` | 1 |
| `The expert doesn't take any action to analyze the image but directly reaches the conclusion that the background is the E` | 1 |
| `WebSurfer encountered difficulties in locating and accessing the acknowledgment section of the paper, causing a delay in` | 1 |
| `The Orchestrator should not directly decide to check other criteria. In fact, WebSurfer did not provide a full list of s` | 1 |
| `The data provided by the Data_Collection_Expert for the reference works in Life Science and Health Sciences is incorrect` | 1 |
| `The agent should provide a transcription of the audio file to extract the page numbers, but it failed to transcribe the ` | 1 |
| `It did not return anything useful.` | 1 |
| `The WebSurfer should find the clickable link to the APOD image for the first week of August 2015 and extract the city na` | 1 |
| `WebSurfer returned general and unrelated information due to poorly refined queries and failed to identify the specific v` | 1 |
| `The WebSurfer does not click on useful information.` | 1 |
| `FileSurfer failed to access the article due to a 404 File Not Found error, leading to an incorrect guess (tricksy) inste` | 1 |
| `There is no membership information.` | 1 |
| `The Orchestrator should instruct WebSurfer to search for hikes on TripAdvisor to verify the ratings and review counts, i` | 1 |
| `The WebSurfer should visit TripAdvisor pages for specific trails to verify the number of reviews, average rating, instea` | 1 |
| `The Orchestrator should instruct WebSurfer to search for the professional history of each board member to determine whet` | 1 |
| `The caculation is wrong.` | 1 |
| `The Orchestrator should not directly draw a conclusion if enough information has not been gathered to answer the query. ` | 1 |
| `WebSurfer should refer to the list of funds on Fidelity's official website to find the correct answer and should not rel` | 1 |
| `The agent provides information about the current roster, but the question asks for the roster as of July 2023. THe agent` | 1 |
| `The WebSurfer did not provide the correct OCR text for the lyrics of the song 'Human Nature' by Michael Jackson in the b` | 1 |
| `The instrcution is wrong.` | 1 |
| `The Orchestrator should not decide to replan. WebSurfer has already triggered the button for 2020, but the Orchestrator ` | 1 |
| `It failed to extract useful information from the Issue page.` | 1 |
| `The WebSurfer did not return the useful information needed to answer the question.` | 1 |
| `The Orchestrator should not replan. The answer is in the previous step, while it should try to verify the birthdate of t` | 1 |
| `The search results of WebSurfer did not include the gym 'Avea Pilates' which is near Tompkins Square Park.` | 1 |
| `The websurfer did not actually enter the location and click the view. Therefore the website keeps on the same page and t` | 1 |
| `The retrieved information is not useful.` | 1 |
| `The information obtained by WebSurfer is neither reliable nor satisfies the requirements of the Orchestrator.` | 1 |
| `FileSurfer didn't correctly extract the relevant information but directly gave a wrong answer.` | 1 |
| `Assistant naviagtes the agents group to a wrong direction - contacting the offices for the result. Instead, the agents s` | 1 |
| `The list of gyms within 5 miles of 400 Main Street, Point Pleasant, WV 25550 is actually not shown in full at step 8. Th` | 1 |
| `WebSurfer failed to locate the specific volume in the University of Leicester paper due to incomplete data retrieval fro` | 1 |
| `WebSurfer clicks on an irrelevant website and disrupts the task-solving process.` | 1 |
| `The information it obtains is incorrect.` | 1 |
| `The agent should recognize that the website has clickable and expandable tabs containing the full rhyme for each flavor.` | 1 |
| `The search tool does not return the desired information regarding the passenger count of each train in 2019. Therefore, ` | 1 |
| `The searching result is wrong.` | 1 |
| `WebSurfer failed to provide useful information and encountered errors during the process.` | 1 |
| `The assistant agent makes calculations with factual errors. The density of liquid Freon-12 under the required conditions` | 1 |
| `When listing the top 10 domestic movies, the assistant omitted 'Demon Slayer: Kimetsu no Yaiba - The Movie: Mugen Train'` | 1 |
| `The Orchestrator encountered an error while processing the data.` | 1 |
| `It provides incorrect instructions.` | 1 |
| `The Orchestrator made an error when performing the translation.` | 1 |
| `The reasoning process is wrong.` | 1 |
| `The agent didn't find enough information to answer the question but directly gave the answer.` | 1 |
| `The Orchestrator should count the total number of revisions. The task has not yet been fully completed.` | 1 |
| `The steps to solve this question are completely irrelevant to the question.` | 1 |
| `The expert fails to view the image and hallucinates the notes.` | 1 |
| `The agent writes code using pandas, which cannot handle the color data in the Excel file. As a result, the code fails to` | 1 |
| `The Python code is incorrect.` | 1 |
| `The price in this Python program is not the actual price, yet the Verification_Expert directly used it for calculation.` | 1 |
| `The expert made a factual error. Thriller is not a song but an album.` | 1 |
| `The list of films provided by the Filmography_Expert is incorrect.` | 1 |
| `The code provided by the Verification_Expert is unreasonable.` | 1 |
| `The conversion process from the Babylonian number system to decimal numbers is flawed, which would result in an incorrec` | 1 |
| `The agent fabricated the population figures for Seattle and Colville, resulting in an incorrect calculation of the popul` | 1 |
| `The agent incorrectly assumes that there are 20 blocks per mile. According to available sources, in Chicago, one mile co` | 1 |
| `The agent provided information that is completely irrelevant to the problems.` | 1 |
| `The proposed method to solve the problem is incorrect because no Python code is provided.` | 1 |
| `The expert does not verify the schedule; instead, it merely assumes that the schedule is correct.` | 1 |
| `The agent directly reaches a conclusion without taking any actual actions.` | 1 |
| `Instead of browsing the web, the agent fabricates the process of data collection and verification.` | 1 |
| `The Verification_Expert fails to identify issues with other agents, namely the Fitness_Expert and Local_Knowledge_Expert` | 1 |
| `The WomenInComputerScienceHistory_Expert did not extract the correct information. The end year should be 2017, not 2022.` | 1 |
| `The code provided by DataExtraction_Expert is incorrect. Executing the code did not yield the correct information.` | 1 |
| `The code provided by FinancialData_Expert is incorrect.` | 1 |
| `The expert did not perform any verifications and instead directly gave the conclusion.` | 1 |
| `The Culinary_Expert incorrectly included 'salt' as an ingredient and misinterpreted 'fresh strawberries' as 'ripe strawb` | 1 |
| `The expert directly reached a conclusion without further verifying the search results. The OpenCV contribution list is i` | 1 |
| `The expert wrote code with bugs, leading the following experts to follow the same method for extracting winner informati` | 1 |
| `The answer provided by Cubing_Expert was incorrect.` | 1 |
| `The agent wrote incorrect code to calculate the desired value.` | 1 |
| `The AnimalBehavior_Expert provides no useful information.` | 1 |
| `The plan to solve the problem is incorrect.` | 1 |
| `The agent made an error in the simulation implementation, resulting in an incorrect outcome.` | 1 |
| `The agent assumes that the video is available for download, exhausting the step limit.` | 1 |
| `The script failed to locate the C++ code on the webpage because it was not targeting the correct elements. Despite multi` | 1 |
| `The expert misinterprets the output of the OCR function and provides the simplified fractions in an incorrect format.` | 1 |
| `The code is incorrect, as executing it returns no output.` | 1 |
| `The reasoning provided by Tizin_Translation_Expert is incorrect, as the accusative case should be used instead of the no` | 1 |
| `The agent hallucinates the video ID and calls the tool with placeholder data. The task is not attempted.` | 1 |
| `The Paintball_Expert provides incorrect addresses for karting tracks and paintball venues in Cologne, Germany. The exper` | 1 |
| `The agent assumes the existence of the file houston_weather_june_2020_2023.csv, which is not provided in the task. The a` | 1 |
| `The agent made a mistake in rounding the calculated time to the nearest 1,000 hours. The calculated time was approximate` | 1 |
| `The code calls the arxiv_search tool; however, using other tools, such as perform_web_search, would be more appropriate ` | 1 |
| `Made an incorrect assumption that the PDF file was available and accessible.` | 1 |
| `The agent failed to locate the correct URL for the dataset from the USGS Nonindigenous Aquatic Species database.` | 1 |
| `The expert failed to identify the correct title of the first paper authored by Pietro Murano.` | 1 |
| `The code provided by the BingAPI_Expert is incorrect.` | 1 |
| `The conversation did not verify the exact recycling rate from the Wikipedia link, which was a crucial step in validating` | 1 |
| `The step assumed the extracted population value (56,583) was the 2020 estimate without verifying its accuracy or time fr` | 1 |
| `Give the wrong final answer and directly reach an incorrect conclusion.` | 1 |
| `The agent made an error in identifying the first place mentioned by name in the Book of Esther (NIV). It incorrectly ide` | 1 |
| `The question is not related to Python. He misunderstood the problem and failed to solve it.` | 1 |
| `While obtaining the web link, the expert should download the PDF file and extract the corresponding text. They should no` | 1 |
| `The expert should not use OCR, and analyzing data is not the responsibility of the Validation_Expert, leading to the exh` | 1 |
| `The Verification_Expert does not question the 0% result, which is highly unusual. It should take responsibility for furt` | 1 |
| `The agent incorrectly assumed the polygon to be a regular hexagon.` | 1 |
| `The Verification_Expert generates an inaccurate summary of the search results and overlooks the original query, which sp` | 1 |
| `The information provided initially is incorrect, leading to an incorrect conclusion.` | 1 |
| `The agent begins using placeholder values in the code, which results in failure.` | 1 |
| `The time of the oldest closed issue is not the same as the time when the 'Regression' label was added to the issue. The ` | 1 |
| `The code provided by MilitaryHistory_Expert is unreasonable, as it is overly hasty. He should investigate step by step i` | 1 |
| `The code provided by WebDevelopment_Expert is incorrect.` | 1 |
| `The task description and focus were unrelated to the actual question of identifying cities based on university locations` | 1 |
| `The agent fabricates the content of the website and does not actually verify its contents.` | 1 |
| `The answer provided by WebServing_Expert was incorrect.` | 1 |
| `The CorporateHistory_IPOs_MondayCom_Expert repeatedly writes incorrect code and provides inaccurate information in step ` | 1 |
| `The agent made a mistake in handling the NaN values in the 'Platform' column by dropping all NaN values from the DataFra` | 1 |
| `The expert made a factual error. The execution result is Braintree, Massachusetts, and Honolulu, Hawaii, rather than Hon` | 1 |
| `According to the answer, the album Tidal by Fiona Apple did not receive a letter grade from Robert Christgau. However, t` | 1 |
| `To answer the question, the agent should not make any assumptions.` | 1 |
| `The agent made a mistake in calculating the total number of wheels for the steam locomotives. The Whyte notation directl` | 1 |
| `The verification process is incorrect. It should provide the most relevant link; instead, it provides a summary of the s` | 1 |
| `The expert provided the setting as 'INT. CASTLE BEDROOM' instead of the correct setting, 'THE CASTLE.'` | 1 |
| `Using YouTube tools is more appropriate.` | 1 |
| `The agent wrote incorrect code twice, exhausting the interaction limits.` | 1 |
| `The assistant provides an incorrect plan in response to an inaccurate question.` | 1 |
| `The expert uses placeholders in the code to fetch data from an API, resulting in errors due to missing actual values.` | 1 |
| `The code failed to handle edge cases in the 'Street Address' data, leading to an incomplete and inaccurate count of even` | 1 |
| `Incorrectly identified the background headstone in the photo of Dastardly Mash as Crème Brulee, leading to the extractio` | 1 |
| `The experts provide factual inaccuracies.` | 1 |
| `The code is incorrect because it did not import the perform_web_search function.` | 1 |
| `The expert should continue examining the search results for the remaining board members to finalize the findings.` | 1 |
| `The code is incorrect because it attempts to extract columns that do not exist.` | 1 |
| `The agent made a logical error in reasoning about scenario 2. If there is at least one vampire, then the statement 'At l` | 1 |
| `The code provided by SpeciesSightingsData_Expert is incorrect.` | 1 |
| `The code is wrong` | 1 |
| `The agent starts by generating a simulated dataset and then processes the data to identify the country with the least nu` | 1 |
| `The code is not appropriate for the task.` | 1 |
| `The agent should use Python to obtain the website content and extract the chapter numbers quoted in the titles of the pa` | 1 |
| `The code provided by DataVerification_Expert is not working, resulting in the failure of execution.` | 1 |
| `The Verification_Expert provided incorrect code to solve the task.` | 1 |
| `The agent uses its internal knowledge to list the stops on the Franklin-Foxboro line instead of searching for the most a` | 1 |
| `The agent makes an incorrect assumption that the total number of articles is 1,000. However, the exact number of article` | 1 |
| `WebSurfer's OCR did not correctly extract the required information (the prices of daily and season passes), leading the ` | 1 |

### 2.5 Частоты: mistake_step (топ-20)

| mistake_step | Кол-во |
|------|------|
| `1` | 35 |
| `8` | 22 |
| `0` | 20 |
| `4` | 19 |
| `5` | 17 |
| `3` | 15 |
| `2` | 11 |
| `12` | 8 |
| `6` | 7 |
| `7` | 4 |
| `9` | 4 |
| `16` | 3 |
| `32` | 3 |
| `24` | 2 |
| `18` | 2 |
| `51` | 2 |
| `82` | 1 |
| `20` | 1 |
| `15` | 1 |
| `39` | 1 |


### 3.1 Аннотированный: magentic_one.jsonl

**Записей:** 44  **Всего failures:** 295


**Схема failures:**

| Поле | Тип |
|------|------|
| `failure_id` | `object` |
| `step_number` | `int64` |
| `step_reason` | `object` |
| `failure_category` | `object` |
| `category_reason` | `object` |
| `failed_agent` | `object` |

**failure_category частоты:**

| failure_category | Кол-во |
|------|------|
| `Instruction/Plan Adherence Failure` | 197 |
| `Guardrails Triggered` | 24 |
| `Misinterpretation of Tool Output` | 23 |
| `Intent not supported` | 22 |
| `Intent Plan Misalignment` | 19 |
| `Invention of new information` | 8 |
| `Invalid Invocation` | 1 |
| `System Failure` | 1 |

**failed_agent частоты:**

| failed_agent | Кол-во |
|------|------|
| `WebSurfer` | 207 |
| `Orchestrator` | 67 |
| `Websurfer` | 13 |
| `FileSurfer` | 5 |
| `Assistant` | 3 |

**root_cause_reason (уникальных):** 43

**Примеры root_cause_reason:**
- `The Orchestrator could tried to recover from earlier errors but the FileSurfer hallucination was a critical failure that prevented further progress.`
- `The Orchestrator failed to properly assess the page coverage reported by the Websurfer agent and proceeded with incomplete data.`
- `The Websurfer agent was unable to bypass the Cloudflare protection, which is a common barrier for automated agents.`

**Пример записи (magentic_one.jsonl):**
```json
{
  "trajectory_id": "5f982798-16b9-4051-ab57-cfc7ebdb2a91",
  "num_failures": 3,
  "root_cause_reason": "The Orchestrator could tried to recover from earlier errors but the FileSurfer hallucination was a critical failure that prevented further progress.",
  "failures_sample": [
    {
      "failure_id": "1",
      "step_number": 13,
      "step_reason": "Websurfer could not  download a PDF file and search throught it which was an instruction given by Orchestrator.",
      "failure_category": "Instruction/Plan Adherence Failure",
      "category_reason": "Instruction not followed, the agent did not download and search through the PDF file as instructed",
      "failed_agent": "Websurfer"
    },
    {
      "failure_id": "2",
      "step_number": 17,
      "step_reason": "Websurfer could not  download a PDF file and search throught it which was an instruction given by Orchestrator",
      "failure_category": "Instruction/Plan Adherence Failure",
      "category_reason": "Websurfer could not  download a PDF file and search throught it which was an instruction given by Orchestrator",
      "failed_agent": "Websurfer"
    }
  ]
}
```

### 3.1 Аннотированный: tau_retail.jsonl

**Записей:** 29  **Всего failures:** 39


**Схема failures:**

| Поле | Тип |
|------|------|
| `failure_id` | `object` |
| `step_number` | `int64` |
| `step_reason` | `object` |
| `failure_category` | `object` |
| `category_reason` | `object` |
| `failed_agent` | `object` |

**failure_category частоты:**

| failure_category | Кол-во |
|------|------|
| `Underspecified User Intent` | 10 |
| `Misinterpretation of Tool Output` | 8 |
| `Intent Plan Misalignment` | 8 |
| `Instruction Adherence Failure` | 6 |
| `Invalid Invocation` | 4 |
| `Intent Not Supported` | 2 |
| `System Failure` | 1 |

**failed_agent частоты:**

| failed_agent | Кол-во |
|------|------|
| `Assistant` | 29 |
| `User` | 10 |

**root_cause_reason (уникальных):** 26

**Примеры root_cause_reason:**
- `The assistant finally did authenticate before providing user specific information. The incorrect count does not correspond with ground truth output.`
- `The assistant finally did authenticate before providing user specific information. The incorrect count does not correspond with ground truth output.`
- `The incorrect count does not correspond with ground truth output.`

**Пример записи (tau_retail.jsonl):**
```json
{
  "trajectory_id": "2",
  "num_failures": 2,
  "root_cause_reason": "The assistant finally did authenticate before providing user specific information. The incorrect count does not correspond with ground truth output.",
  "failures_sample": [
    {
      "failure_id": "1",
      "step_number": 3,
      "step_reason": "At step 3, the assistant agent did not authenticate user information before proceeding to provide information about available t-shirts",
      "failure_category": "Instruction Adherence Failure",
      "category_reason": "The assistant agent did not follow the expected policy of authenticating user information before providing product details.",
      "failed_agent": "Assistant"
    },
    {
      "failure_id": "2",
      "step_number": 7,
      "step_reason": "At step 7, the agent did not correctly count the number of available t-shirts from the tool call result.",
      "failure_category": "Misinterpretation of Tool Output",
      "category_reason": "The assistant misinterpreted the output from the tool call, leading to an incorrect count of available t-shirts.",
      "failed_agent": "Assistant"
    }
  ]
}
```

### 3.2 Только траектории: magentic_dataset.jsonl

**Записей:** 58

**Ключи верхнего уровня:** ['trajectory_id', 'instruction', 'steps']


**Типы значений:**

- `trajectory_id`: `str`
- `instruction`: `str`
- `steps`: `list`

**Пример первого шага (len(steps)=129):**

```json
{
  "index": 1,
  "substeps": [
    {
      "sub_index": 1,
      "role": "human",
      "content": "According to Google Finance, when was the first year the Apple stock went above $50 (without adjusting for stock split)?\n"
    }
  ]
}
```

**Статус:** типизация ошибок отсутствует — только траектории


### 3.2 Только траектории: tau_retail_dataset.jsonl

**Записей:** 29

**Ключи верхнего уровня:** ['trajectory_id', 'instruction', 'steps']


**Типы значений:**

- `trajectory_id`: `str`
- `instruction`: `str`
- `steps`: `list`

**Пример первого шага (len(steps)=32):**

```json
{
  "index": 1,
  "substeps": [
    {
      "sub_index": 1,
      "role": "system",
      "content": "# Retail agent policy\n\nAs a retail agent, you can help users cancel or modify pending orders, return or exchange delivered orders, modify their default user address, or provide information about their own profile, orders, and related products.\n\n- At the beginning of the conversation, you have to authenticate the user identity by locating their user id via email, or via name + zip code. This has to be done even when the user already provides the user id.\n\n- Once the user has been authenti
```

**Статус:** типизация ошибок отсутствует — только траектории


### 3.3 Combined: failure_category across all annotated files

**Всего failures (оба файла):** 334


**Combined failure_category (оба файла):**

| failure_category | Кол-во |
|------|------|
| `Instruction/Plan Adherence Failure` | 197 |
| `Misinterpretation of Tool Output` | 31 |
| `Intent Plan Misalignment` | 27 |
| `Guardrails Triggered` | 24 |
| `Intent not supported` | 22 |
| `Underspecified User Intent` | 10 |
| `Invention of new information` | 8 |
| `Instruction Adherence Failure` | 6 |
| `Invalid Invocation` | 5 |
| `System Failure` | 2 |
| `Intent Not Supported` | 2 |

## 4. Пять дополнительных датасетов

### 4.1 nebius/SWE-agent-trajectories

**Паркет-файлов:** 12
**Всего строк:** ~80,036

**Схема (top-level columns):**

- `instance_id`: `String`
- `model_name`: `String`
- `target`: `Boolean`
- `trajectory`: `List(Struct({'cutoff_date': String, 'mask': Boolean, 'role': String, 'system_prompt': String, 'text': String}))`
- `exit_status`: `String`
- `generated_patch`: `String`
- `eval_logs`: `String`

**Поле `exit_status` — уникальные значения в выборке:** {'submitted', 'submitted (exit_context)'}

**exit_status (5 rows):**
shape: (2, 2)
┌──────────────────────────┬───────┐
│ exit_status              ┆ count │
│ ---                      ┆ ---   │
│ str                      ┆ u32   │
╞══════════════════════════╪═══════╡
│ submitted (exit_context) ┆ 3     │
│ submitted                ┆ 2     │
└──────────────────────────┴───────┘

**Пример шага траектории (len=93):**
`{'cutoff_date': '01.01.2023', 'mask': False, 'role': 'system', 'system_prompt': "SETTING: You are an autonomous programmer, and you're working directly in the command line with a special interface.\n\nThe special interface consists of a file editor that shows you 100 lines of a file at a time.\nIn addition to typical bash commands, you can also use the following commands to help you navigate and edit files.\n\nCOMMANDS:\nopen:\n  docstring: opens the file at the given path in the editor. If line_number is provided, the window will be move to include that line\n  signature: open <path> [<line_n…`

### 4.2 SWE-Gym/OpenHands-Sampled-Trajectories

**Паркет-файлов:** 4
**Всего строк:** 6,055

**Схема:**


**Схема:**

- `instance_id`: `String`
- `run_id`: `String`
- `resolved`: `Boolean`
- `messages`: `List(Struct({'content': String, 'function_call': Null, 'name': String, 'role': String, 'tool_call_id': String, 'tool_calls': List(Struct({'function': Struct({'arguments': String, 'name': String}), 'id': String, 'index': Int64, 'type': String}))}))`
- `tools`: `List(Struct({'function': Struct({'description': String, 'name': String, 'parameters': Struct({'properties': Struct({'command': Struct({'description': String, 'enum': List(String), 'type': String}), 'file_text': Struct({'description': String, 'type': String}), 'insert_line': Struct({'description': String, 'type': String}), 'new_str': Struct({'description': String, 'type': String}), 'old_str': Struct({'description': String, 'type': String}), 'path': Struct({'description': String, 'type': String}), 'view_range': Struct({'description': String, 'items': Struct({'type': String}), 'type': String})}), 'required': List(String), 'type': String})}), 'type': String}))`
- `test_result`: `Struct({'apply_patch_output': String, 'git_patch': String, 'report': Struct({'empty_generation': Boolean, 'error_eval': Boolean, 'failed_apply_patch': Boolean, 'resolved': Boolean, 'test_timeout': Boolean}), 'test_output': String})`

**Error-related fields:** ['resolved']
  `resolved`: [False, False, False, False, False]

**Пример первого сообщения (len=9):**
`{'content': "You are a helpful assistant that can interact with a computer to solve tasks.\n<IMPORTANT>\n* If user provides a path, you should NOT assume it's relative to the current working directory. Instead, you should explore the file system to find the file before working on it.\n</IMPORTANT>\n", 'function_call': None, 'name': None, 'role': 'system', 'tool_call_id': None, 'tool_calls': None}`

### 4.3 yoonholee/terminalbench-trajectories

**Паркет-файлов:** 2
**Всего строк:** 52,104

**Схема:**

- `task_name`: `String`
- `agent`: `String`
- `model`: `String`
- `reward`: `Int64`
- `duration_seconds`: `Float64`
- `input_tokens`: `Float64`
- `output_tokens`: `Float64`
- `cache_tokens`: `Float64`
- `cost_cents`: `Float64`
- `trial_name`: `String`
- `trial_id`: `String`
- `started_at`: `String`
- `ended_at`: `String`
- `steps`: `String`

**steps sample (type=str):**
`'null'`

### 4.4 ibm-research/ITBench-Trajectories

**session.jsonl файлов:** 105
**Прочитано записей из первого файла:** 5

**Ключи верхнего уровня (первая запись):**

- `timestamp`: `str`
- `type`: `str`
- `payload`: `dict`

**type field values in 5 records:**
  {'session_meta', 'response_item', 'event_msg'}

**Пример payload:**
`{'id': '019b76a6-7641-7aa1-968f-f3564b8e8078', 'timestamp': '2025-12-31T23:02:59.393Z', 'cwd': '/root/projects/open_source/zero/leaderboard_results/react with code_openai_gpt-oss-120b_07ccdb1/Scenario-1/2', 'originator': 'codex_exec', 'cli_version': '0.76.0', 'instructions': '**Task**: \n\nYou are an expert SRE (Site Reliability Engineer) and Kubernetes SRE Support Agent investigating a production incident from OFFLINE snapshot data.\n\nYou are a highly capable tool-using agent able to:\n- Diagnose Kubernetes failures\n- Correlate alerts, events, traces, and metrics\n- Identify contributing fa…`

### 4.5 iMeanAI/Mind2Web-Live

**Файл:** mind2web-live_test_20241024.json
**Прочитано строк:** 5

**Схема:**

- `index`: `int64`
- `task`: `object`
- `reference_task_length`: `int64`
- `evaluation`: `object`

**Пример evaluation:**
`[{'match_function_name': 'url_included_match', 'content': {'key': '', 'reference_answer': 'gamestop.', 'url': 'https://www.gamestop.com/'}}, {'match_function_name': 'url_exactly_match', 'content': {'key': 'store', 'reference_answer': '2630', 'url': 'https://www.gamestop.com/search/?store=2630'}}]`

## 5. Вывод

**Who&When** — ✅ Есть явная типизация. Поля: `mistake_agent`, `mistake_step`, `mistake_reason` (182 уникальных free-text значений). 184 записи — все неуспешные. mistake_reason свободный текст, не фиксированная таксономия.

**AgentRx** — ⚠️ Частичная типизация. 73 из 159 записей аннотированы. `failure_category` имеет 8+ категорий, но таксономия НЕ унифицирована между файлами (magentic_one ≠ tau_retail). `failed_agent` доминирует WebSurfer.

**nebius/SWE-agent** — ❌ Нет типизации. Только `exit_status` (3 категории: exit_context/exit_format/early_exit). Можно извлечь: частоту успех/провал, длину траектории, модель.

**SWE-Gym/OpenHands** — ❌ Нет типизации. Только `resolved` (bool) и `test_result` (bool flags без таксономии). Можно извлечь: success rate, длину сообщений.

**yoonholee/terminalbench** — ❌ Нет типизации. Только `reward` (binary 0/1) и `duration_seconds`. Можно извлечь: success rate, время выполнения, стоимость.

**ibm-research/ITBench** — ⚠️ Частично. session.jsonl содержит `type: error` но это operational message type, не структурированная таксономия. Можно извлечь: оценки качества из judge_output, типы операций.

**iMeanAI/Mind2Web-Live** — ❌ Нет типизации. Нет траекторий, только описания задач и критерии оценки. Можно извлечь: число задач, complexity.



**Итого:** из 7 датасетов только Who&When и AgentRx имеют структурированную типизацию ошибок. Остальные 5 — только агрегированные метрики (exit_status, resolved, reward). Для ТЗ №2 основной фокус — на парсерах Who&When и AgentRx.