import logging

# silence fastapi warning about email-validator
logging.getLogger("fastapi").setLevel(logging.ERROR)
