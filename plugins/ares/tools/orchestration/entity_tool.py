from __future__ import annotations

import json

from plugins.ares.tools.base import json_result
from plugins.ares.state import engagement_store as store

TOOLSET = "ares_utility"


def _handle_save(args: dict, **kw) -> str:
    eng = store.get_engagement()
    if not eng:
        return json_result(False, error="No active engagement. Call engage_init first.")
    entity_type = args.get("type", "")
    name = args.get("name", "")
    if not entity_type or not name:
        return json_result(False, error="type and name are required")
    data = args.get("data")
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            data = {"raw": data}
    confidence = args.get("confidence", 1.0)
    verified = args.get("verified", False)
    parent_id = args.get("parent_id")
    eid = store.save_entity(
        engagement_id=eng.id,
        entity_type=entity_type,
        name=name,
        data=data,
        confidence=confidence,
        verified=verified,
        parent_id=parent_id,
    )
    return json_result(True, data={"entity_id": eid, "type": entity_type, "name": name})


def _handle_query(args: dict, **kw) -> str:
    eng = store.get_engagement()
    if not eng:
        return json_result(False, error="No active engagement.")
    entity_type = args.get("type")
    name_pattern = args.get("name")
    limit = args.get("limit", 50)
    entities = store.query_entities(eng.id, entity_type=entity_type, name_pattern=name_pattern, limit=limit)
    return json_result(True, data={
        "count": len(entities),
        "entities": [e.to_dict() for e in entities],
    })


def _handle_graph(args: dict, **kw) -> str:
    eng = store.get_engagement()
    if not eng:
        return json_result(False, error="No active engagement.")
    entity_id = args.get("entity_id")
    if entity_id:
        neighbors = store.get_neighbors(entity_id, direction="both")
        entity = store.get_entity(entity_id)
        if not entity:
            return json_result(False, error="Entity not found")
        return json_result(True, data={
            "entity": entity.to_dict(),
            "neighbors": neighbors,
            "neighbor_count": len(neighbors),
        })
    graph = store.get_full_graph(eng.id)
    return json_result(True, data={
        "entity_count": len(graph.entities),
        "relationship_count": len(graph.relationships),
        "graph": graph.to_dict(),
    })


def _handle_link(args: dict, **kw) -> str:
    eng = store.get_engagement()
    if not eng:
        return json_result(False, error="No active engagement.")
    source_id = args.get("source_id")
    target_id = args.get("target_id")
    relation = args.get("relation", "")
    if not source_id or not target_id or not relation:
        return json_result(False, error="source_id, target_id, and relation are required")
    data = args.get("data")
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            data = {}
    confidence = args.get("confidence", 1.0)
    rid = store.add_relationship(
        engagement_id=eng.id,
        source_id=source_id,
        target_id=target_id,
        relation=relation,
        data=data,
        confidence=confidence,
    )
    return json_result(True, data={"relationship_id": rid, "relation": relation})


def _handle_count(args: dict, **kw) -> str:
    eng = store.get_engagement()
    if not eng:
        return json_result(False, error="No active engagement.")
    counts = store.count_entities(eng.id)
    return json_result(True, data={"engagement_id": eng.id, "entities": counts, "total": sum(counts.values())})


_SAVE_SCHEMA = {
    "name": "entity_save",
    "description": "Save a discovered entity to the knowledge graph. Use this for every discovered host, port, service, technology, vulnerability, credential, or user. Entities are linked to the current engagement.",
    "parameters": {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": list(store.ENTITY_TYPES) if hasattr(store, "ENTITY_TYPES") else [
                    "host", "domain", "subdomain", "port", "service",
                    "technology", "credential", "user", "group",
                    "finding", "vulnerability",
                ],
                "description": "Entity type",
            },
            "name": {"type": "string", "description": "Entity name (e.g. '10.10.10.10', 'Apache/2.4.57', 'WordPress')"},
            "data": {"type": "object", "description": "Additional data as JSON (e.g. {port: 80, protocol: 'tcp', version: '2.4.57'})"},
            "confidence": {"type": "number", "description": "Confidence score 0.0-1.0 (default: 1.0)"},
            "verified": {"type": "boolean", "description": "Whether this entity has been verified (default: false)"},
            "parent_id": {"type": "integer", "description": "Parent entity ID (e.g. service belongs to host)"},
        },
        "required": ["type", "name"],
    },
}

_QUERY_SCHEMA = {
    "name": "entity_query",
    "description": "Query entities in the knowledge graph. Filter by type and/or name pattern. Returns matching entities with their data.",
    "parameters": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "description": "Filter by entity type"},
            "name": {"type": "string", "description": "Filter by name (partial match)"},
            "limit": {"type": "integer", "description": "Max results (default 50)"},
        },
    },
}

_GRAPH_SCHEMA = {
    "name": "entity_graph",
    "description": "Get the knowledge graph. Without parameters returns the full graph. With entity_id returns that entity's connections. Use to understand relationships between discovered objects.",
    "parameters": {
        "type": "object",
        "properties": {
            "entity_id": {"type": "integer", "description": "Get connections for a specific entity (optional)"},
        },
    },
}

_LINK_SCHEMA = {
    "name": "entity_link",
    "description": "Create a relationship between two entities in the knowledge graph. Use to connect hosts to services, services to vulnerabilities, etc.",
    "parameters": {
        "type": "object",
        "properties": {
            "source_id": {"type": "integer", "description": "Source entity ID"},
            "target_id": {"type": "integer", "description": "Target entity ID"},
            "relation": {
                "type": "string",
                "enum": [
                    "runs_on", "has_port", "has_service", "uses_tech",
                    "has_vulnerability", "discovered_by", "authenticated_with",
                    "references_cve", "exploits", "depends_on", "member_of",
                    "connected_to", "resolves_to", "hosted_on", "subdomain_of",
                ],
                "description": "Relationship type",
            },
            "data": {"type": "object", "description": "Additional relationship data"},
            "confidence": {"type": "number", "description": "Confidence 0.0-1.0"},
        },
        "required": ["source_id", "target_id", "relation"],
    },
}

_COUNT_SCHEMA = {
    "name": "entity_count",
    "description": "Get entity counts by type for the current engagement.",
    "parameters": {"type": "object", "properties": {}},
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="entity_save",
        toolset=TOOLSET,
        schema=_SAVE_SCHEMA,
        handler=lambda args, **kw: _handle_save(args, **kw),
        emoji="🧠",
    )
    ctx.register_tool(
        name="entity_query",
        toolset=TOOLSET,
        schema=_QUERY_SCHEMA,
        handler=lambda args, **kw: _handle_query(args, **kw),
        emoji="🔍",
    )
    ctx.register_tool(
        name="entity_graph",
        toolset=TOOLSET,
        schema=_GRAPH_SCHEMA,
        handler=lambda args, **kw: _handle_graph(args, **kw),
        emoji="🕸️",
    )
    ctx.register_tool(
        name="entity_link",
        toolset=TOOLSET,
        schema=_LINK_SCHEMA,
        handler=lambda args, **kw: _handle_link(args, **kw),
        emoji="🔗",
    )
    ctx.register_tool(
        name="entity_count",
        toolset=TOOLSET,
        schema=_COUNT_SCHEMA,
        handler=lambda args, **kw: _handle_count(args, **kw),
        emoji="📊",
    )
