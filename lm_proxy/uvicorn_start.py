import os
import dotenv
import uvicorn

def uvicorn_start():
    dotenv.load_dotenv('.env')
    uvicorn.run(
        "lm_proxy.app:app",
        host=os.getenv("LM_PROXY_HOST", "0.0.0.0"),
        port=int(os.getenv("LM_PROXY_PORT", 8000)),
        reload=False,  # autoreload
    )
