from datetime import datetime, timezone
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import schemas, services
from app.persistance import models
from app.persistance.database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Network Route Optimization API",
    description="Manage a directed network and calculate minimum-latency routes using Dijkstra's algorithm.",
    version="1.0.0",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"detail": exc.errors()})


def get_node_or_404(db: Session, node_id: int):
    node = db.get(models.Node, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@app.post("/nodes", response_model=schemas.NodeOut, status_code=201)
def add_node(payload: schemas.NodeCreate, db: Session = Depends(get_db)):
    if db.query(models.Node).filter(models.Node.name == payload.name).first():
        raise HTTPException(status_code=400, detail="Node name already exists")
    node = models.Node(name=payload.name)
    db.add(node)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Node name already exists")
    db.refresh(node)
    return node


@app.get("/nodes", response_model=list[schemas.NodeOut])
def list_nodes(db: Session = Depends(get_db)):
    return db.query(models.Node).order_by(models.Node.id).all()


@app.delete("/nodes/{node_id}", status_code=204)
def delete_node(node_id: int, db: Session = Depends(get_db)):
    node = get_node_or_404(db, node_id)
    db.query(models.Edge).filter(
        (models.Edge.source_id == node_id) | (models.Edge.destination_id == node_id)
    ).delete(synchronize_session=False)
    db.delete(node)
    db.commit()
    return None


@app.post("/edges", response_model=schemas.EdgeOut, status_code=201)
def add_edge(payload: schemas.EdgeCreate, db: Session = Depends(get_db)):
    source = db.query(models.Node).filter(models.Node.name == payload.source).first()
    destination = db.query(models.Node).filter(models.Node.name == payload.destination).first()
    if source is None:
        raise HTTPException(status_code=400, detail=f"Source node '{payload.source}' not found")

    if destination is None:
        raise HTTPException(status_code=400, detail=f"Destination node '{payload.destination}' not found")

    if source.id == destination.id:
        raise HTTPException(status_code=400, detail="Self-loop edges are not supported")
    duplicate = db.query(models.Edge).filter(
        models.Edge.source_id == source.id,
        models.Edge.destination_id == destination.id,
    ).first()

    if duplicate:
        raise HTTPException(status_code=400, detail="Duplicate edge")
    edge = models.Edge(source_id=source.id, destination_id=destination.id, latency=payload.latency)
    db.add(edge)


    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate edge")
    db.refresh(edge)
    return schemas.EdgeOut(id=edge.id, source=source.name, destination=destination.name, latency=edge.latency)


@app.get("/edges", response_model=list[schemas.EdgeOut])
def list_edges(db: Session = Depends(get_db)):
    result = []
    for edge in db.query(models.Edge).order_by(models.Edge.id).all():
        source = db.get(models.Node, edge.source_id)
        destination = db.get(models.Node, edge.destination_id)
        if source is not None and destination is not None:
            result.append(schemas.EdgeOut(
                id=edge.id, source=source.name, destination=destination.name, latency=edge.latency
            ))
    return result


@app.delete("/edges/{edge_id}", status_code=204)
def delete_edge(edge_id: int, db: Session = Depends(get_db)):
    edge = db.get(models.Edge, edge_id)
    if edge is None:
        raise HTTPException(status_code=404, detail="Edge not found")
    db.delete(edge)
    db.commit()
    return None


@app.post("/routes/shortest", response_model=schemas.ShortestRouteResponse)
def shortest_route(payload: schemas.ShortestRouteRequest, db: Session = Depends(get_db)):
    try:
        result = services.find_shortest_path(db, payload.source, payload.destination)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No path exists between {payload.source} and {payload.destination}",
        )
    total_latency, path = result
    record = models.RouteHistory(
        source=payload.source,
        destination=payload.destination,
        total_latency=total_latency,
        path=path,
    )
    db.add(record)
    db.commit()
    return schemas.ShortestRouteResponse(total_latency=total_latency, path=path)


@app.get("/routes/history", response_model=list[schemas.RouteHistoryOut])
def route_history(
    source: str | None = Query(default=None),
    destination: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(models.RouteHistory)
    if source:
        query = query.filter(models.RouteHistory.source == source.strip())
    if destination:
        query = query.filter(models.RouteHistory.destination == destination.strip())
    if date_from:
        if date_from.tzinfo is None:
            date_from = date_from.replace(tzinfo=timezone.utc)
        query = query.filter(models.RouteHistory.created_at >= date_from)
    if date_to:
        if date_to.tzinfo is None:
            date_to = date_to.replace(tzinfo=timezone.utc)
        query = query.filter(models.RouteHistory.created_at <= date_to)
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must be earlier than or equal to date_to")
    return query.order_by(models.RouteHistory.created_at.desc()).limit(limit).all()


@app.get("/health")
def health():
    return {"status": "lessgo"}
