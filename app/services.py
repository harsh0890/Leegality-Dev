import heapq
from collections import defaultdict
from sqlalchemy.orm import Session

from .persistance import models


def find_shortest_path(db: Session, source: str, destination: str) :
    node_rows = db.query(models.Node).all()


    nodes = {node.name: node for node in node_rows}
    names_by_id = {node.id: node.name for node in node_rows}


    if source not in nodes:
        raise ValueError(f"Node '{source}' does not exist")
    if destination not in nodes:
        raise ValueError(f"Node '{destination}' does not exist")

    adjacency = defaultdict(list)
    edges = db.query(models.Edge).all()
    for edge in edges:
        start_name = names_by_id.get(edge.source_id)
        end_name = names_by_id.get(edge.destination_id)
        if start_name is not None and end_name is not None:
            adjacency[start_name].append((end_name, edge.latency))


    distances = {source: 0.0}
    previous = {}
    queue = [(0.0, source)]

    while queue:
        current_distance, current = heapq.heappop(queue)
        if current_distance > distances.get(current, float("inf")):
            continue
        if current == destination :
            break

        for neighbour, weight in adjacency[current] :
            candidate = current_distance + weight
            if candidate < distances.get(neighbour, float("inf")):
                distances[neighbour] = candidate
                previous[neighbour] = current
                heapq.heappush(queue, (candidate, neighbour))

    if destination not in distances :
        return None

    path = []
    current = destination

    while current != source :
        path.append(current)
        current = previous[current]

    path.append(source)
    path.reverse()
    return distances[destination], path
