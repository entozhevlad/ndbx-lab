#!/bin/sh

set -eu

SCHEMA_FILE="/scripts/neo4j/schema.cypher"

cypher() {
  cypher-shell \
    -a "$NEO4J_URL" \
    -u "$NEO4J_USERNAME" \
    -p "$NEO4J_PASSWORD" \
    "$@"
}

wait_for_neo4j() {
  until cypher "RETURN 1" >/dev/null 2>&1; do
    echo "waiting for neo4j at $NEO4J_URL"
    sleep 2
  done
}

wait_for_neo4j

echo "applying schema from $SCHEMA_FILE"
cypher -f "$SCHEMA_FILE"

echo "neo4j schema is ready"
