import os
import re
from dotenv import load_dotenv
from openai import OpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.llms import OpenAI
from langchain.chains import RetrievalQA
from langchain.embeddings import OpenAIEmbeddings


class GptApi:
    def __init__(self):
        load_dotenv()
        self.text = ''
        self.sections = list()
        self.read_textfile()
        self.api_key = os.environ.get('OPENAI_API_KEY')
        self.llm = ChatOpenAI(temperature=0, model="chatgpt-4o-latest", openai_api_key=self.api_key)
        self.client = OpenAI(api_key=self.api_key)
        self.embedding_model = OpenAIEmbeddings(openai_api_key=self.api_key)
        self.embeddings = OpenAIEmbeddings()
        self.vectorstore = Chroma.from_texts(self.sections, self.embedding_model)

        self.retriever = self.vectorstore.as_retriever()
        
    def read_textfile(self):
        with open("data/txt/university_info.txt", "r", encoding="utf-8") as file:
            self.text = file.read()
        # 번호 패턴을 기준으로 split
        # sections = re.split(r'(?<=\d\.)\s+', text)  # 숫자. 뒤에 공백을 기준으로 split
        self.sections = re.split(r'(?<=\d\.)', self.text)[1:]  # 숫자와 점 뒤에서 split, 첫 번째 빈 문자열 제거

        # 첫 번째 섹션이 빈 문자열일 수 있으므로 제거
        if self.sections[0] == "":
            self.sections = self.sections[1:]

        # 결과 확인
        for idx, section in enumerate(self.sections):
            print(f"\n[섹션 {idx + 3}]\n{section[:100]}...")
    
    def search_and_generate_answer(self,query: str):
        # 벡터 스토어에서 쿼리와 유사한 정보를 검색
        results = self.vectorstore.similarity_search(query, k=1)

        context = results[0].page_content
        prompt = f"다음 정보에 기반하여 질문에 답해주세요, 만약 없다면 정보가 없다면 '정보가 없습니다.'라고 출력해줘 \n\n정보: {context}\n\n질문: {query}\n\n답변:"

        # LLM을 이용하여 답변 생성
        answer = self.llm(prompt)

        # 응답에서 content 부분만 추출하여 반환
        return answer.content
    
    def analyze(self,query:str,question:str):
        prompt = f"다음 글을 기반으로 문맥적 요소를 잃지 않되, 최대한 간결하게 질문에 답해줘 \n\n글 : {query}\n\n 질문 : {question}"
        answer = self.llm(prompt)
        return answer.content