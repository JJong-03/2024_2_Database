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
        self.api_key = os.environ.get('OPENAI_API_KEY')
        self.llm = ChatOpenAI(temperature=0, model="chatgpt-4o-latest", openai_api_key=self.api_key)
        self.client = OpenAI(api_key=self.api_key)
        self.embedding_model = OpenAIEmbeddings(openai_api_key=self.api_key)
        self.embeddings = OpenAIEmbeddings()
        self.vectorstore = Chroma.from_texts(self.sections, self.embedding_model)

        self.read_textfile()
        self.retriever = self.vectorstore.as_retriever()