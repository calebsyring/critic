from public.ecr.aws/lambda/python:3.13 as app

# OS
env UV_COMPILE_BYTECODE=1
env UV_LINK_MODE=copy
## Configure for system level install
env UV_PROJECT_ENVIRONMENT=/var/lang/

## uv install
copy --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/

# App
workdir /app

## Build / deps
copy pyproject.toml hatch.toml readme.md uv.lock .
copy src/critic/version.py src/critic/version.py
run --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --inexact

## Source files after the build for better caching/speed when deps haven't changed
copy src/critic src/critic
copy src/lambda_handler.py src

## App Env
env FLASK_DEBUG=0

# Lambda Entry Point
# The lamba runtime environment will use this dotted path as the entry point to our app when
# the lambda function is invoked.  It must be a function, it doesn't handle class methods.
cmd ["lambda_handler.entry"]
