import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate


# Ensure your OpenAI API key is set
api_key = os.environ["GROK_API_KEY"]


def create_policy_qa_chain(pdf_path: str):
    # Step 1: Load the 2-page PDF policy document
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()

    # Step 2: Split the document into manageable chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)

    # Step 3: Create embeddings and store chunks in a FAISS vectorstore
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(splits, embeddings)

    # Step 4: Expose the vectorstore as a retriever
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # Step 5: Define the system prompt for answering questions
    system_prompt = (
        "You are an assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer the question. "
        "If you don't know the answer, say that you don't know.\n\n"
        "Context:\n{context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    # Step 6: Create the modern retrieval chain
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    return rag_chain


# --- Example Usage ---
if __name__ == "__main__":
    # Replace with the path to your actual 2-page PDF
    pdf_file = "Policy-Document.pdf"

    # Initialize the chain
    qa_chain = create_policy_qa_chain(pdf_file)

    # Ask a question
    question = "What is the policy regarding remote work reimbursement?"
    response = qa_chain.invoke({"input": question})

    print(f"Question: {question}\n")
    print(f"Answer: {response['answer']}")