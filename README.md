# Chatbot Demo (FastAPI + LangChain + Redis + Postgres)

Run locally:

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in keys

# server run:
uvicorn app.main:app --reload

# client run:
streamlit run client/streamlit_app.py


```

Docker start redis:

```bash
docker run -d \
  --name redis-server \
  -p 6379:6379 \
  redis:latest
```


This is design doc of the chatbot demo


supported function:
1. take user input and get the openai model response
2. calling openai tool to take actions according to ther user's instructions
3. store user messages in the cache, prune the message to avoid max token
5. implement a rate limitator


the current problem:
1. the time translate is not perfect 
2. the tool calling is not stable
3. if I have more time, I may improve the agent call logic, to avoid fill the context every LLM call. I would also improve the tool calling prompt to make it stable


system component 

- client side (streamlit framework)
    - construct the REST request 

- gateway api 
    - rate limitator
    - init the Chat orchestrator 

Class

- Chat Orchestrator (facade class to handle the request)
    variables
    - prompt manager
    - context store
    - ai agent
    cuntions


- Prompt Builder
    - re-prompt user input (take user info)

- context store
    - retrieval chat history according to user info
    - save user input in the db

- ai agenet
    - call the wrapped model and get response
    - call tools to complete instruction 


