A FastAPI-based application to manage network nodes and directed edges with configurable latency.
Uses Dijkstra's algorithm to calculate the shortest-latency path between nodes.
Built with Python, FastAPI, SQLAlchemy, SQLite, and Pydantic.
Supports node/edge management, shortest-route calculation, and route history tracking.




🎯Steps to start the project🚀
cd ~/{}/Leegality-Dev
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --port 8000