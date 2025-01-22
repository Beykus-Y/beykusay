mkdir bot && cd bot && (
  mkdir handlers middlewares services utils
  type nul > __init__.py
  type nul > main.py
  type nul > config.py
  cd handlers && (
    type nul > __init__.py
    type nul > admin.py
    type nul > common.py
    type nul > errors.py
  ) && cd ..
  cd middlewares && (
    type nul > __init__.py
    type nul > antiflood.py
  ) && cd ..
  cd services && (
    type nul > __init__.py
    type nul > ai.py
    type nul > moderation.py
  ) && cd ..
  cd utils && (
    type nul > __init__.py
    type nul > helpers.py
  ) && cd ..
) && cd ..
type nul > .env
type nul > .gitignore
type nul > requirements.txt