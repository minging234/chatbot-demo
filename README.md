This is design doc of the chatbot demo

supported function:
1. take user input and get the openai model response, prasing the response to get instruction
2. calling openai model to take actions according to ther user's instruction
3. store user messages in the sqlite db
4. store the user context in redis
5. implement a rate limitator

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
    - context manager
    - ai agent
    cuntions


- Prompt Builder
    - re-prompt user input (take user info)

- Response Parser
    - parsing the response

- context manager
    - retrieval chat history according to user info
    - save user input in the db

- ai agenet
    - call the wrapped model and get response
    - call tools to complete instruction 


data class

- user info
    - user id
    - email
    - apikey

- message (map to db)
    - message id
    - chat_id
    - content
    - prompted content
    - middle output (json list)
    - response




# Chatbot Demo (FastAPI + LangChain + Redis + Postgres)

Run locally:

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in keys
uvicorn app.main:app --reload
```

Docker:

```bash
docker build -t chatbot .
docker run --env-file .env -p 8000:8000 chatbot
```
