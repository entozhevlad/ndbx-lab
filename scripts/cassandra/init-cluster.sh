#!/bin/sh

set -eu

CASSANDRA_HOST="$(echo "$CASSANDRA_HOSTS" | cut -d',' -f1)"
SCHEMA_FILE="/scripts/cassandra/schema.cql"

cql() {
  cqlsh "$@" "$CASSANDRA_HOST" "$CASSANDRA_PORT"
}

wait_for_cassandra() {
  until cql -e "DESCRIBE KEYSPACES" >/dev/null 2>&1; do
    echo "waiting for cassandra at $CASSANDRA_HOST:$CASSANDRA_PORT"
    sleep 2
  done
}

wait_for_cassandra

echo "creating keyspace $CASSANDRA_KEYSPACE"
cql -e "CREATE KEYSPACE IF NOT EXISTS $CASSANDRA_KEYSPACE WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};"

echo "applying schema from $SCHEMA_FILE"
cql -k "$CASSANDRA_KEYSPACE" -f "$SCHEMA_FILE"

echo "cassandra schema is ready"
