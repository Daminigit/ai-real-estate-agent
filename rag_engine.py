import os
from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

DB_DIR = "./chroma_db"

def init_rag_engine(brochure_path="project_brochure.md"):
    if not os.path.exists(brochure_path):
        print(f"Brochure not found at {brochure_path}. Cannot initialize RAG.")
        return None
        
    print("Loading and chunking project brochure...")
    
    with open(brochure_path, 'r', encoding='utf-8') as f:
        doc_text = f.read()

    # Split by markdown headers
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_header_splits = markdown_splitter.split_text(doc_text)
    
    # Further split long chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    splits = text_splitter.split_documents(md_header_splits)
    
    print(f"Created {len(splits)} chunks. Initializing Vector DB...")
    
    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings, persist_directory=DB_DIR)
    
    return vectorstore

def get_rag_chain():
    embeddings = OpenAIEmbeddings()
    # Initialize from existing DB
    vectorstore = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    system_prompt = (
        "You are an AI sales agent for Aurelia Heights. Use the following pieces of retrieved context to "
        "answer the question. If you don't know the answer, say that you don't know and offer to connect them "
        "with a human agent. Do not make up information."
        "\n\n"
        "Context: {context}"
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])
    
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    
    return rag_chain

if __name__ == "__main__":
    try:
        init_rag_engine()
        chain = get_rag_chain()
        response = chain.invoke({"input": "What are the amenities available?"})
        print("\nTest Query: What are the amenities available?")
        print("Response:", response["answer"])
    except Exception as e:
        print(f"Error testing RAG: {e}\nEnsure OPENAI_API_KEY is set in your environment.")
