FROM python:3.9-slim

WORKDIR /app
COPY . .
ENV PORT=8080
CMD ["python", "-c", "import http.server; import os; s = http.server.HTTPServer((\"\", int(os.environ.get(\"PORT\", 8080))), http.server.SimpleHTTPRequestHandler); s.serve_forever()"] 