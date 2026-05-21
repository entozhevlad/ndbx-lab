#!/bin/sh

set -eu

mongo_result() {
  mongosh --quiet --host "$1" --port "$2" --eval "$3" 2>/dev/null | tr -d '[:space:]'
}

wait_for_mongo() {
  name="$1"
  host="$2"
  port="$3"

  until mongosh --quiet --host "$host" --port "$port" --eval 'db.adminCommand({ ping: 1 }).ok' >/dev/null 2>&1; do
    echo "waiting for $name at $host:$port"
    sleep 2
  done
}

wait_for_replset_ready() {
  name="$1"
  host="$2"
  port="$3"

  until [ "$(mongo_result "$host" "$port" 'try { const members = rs.status().members; const primaries = members.filter((member) => member.stateStr === "PRIMARY").length; const secondaries = members.filter((member) => member.stateStr === "SECONDARY").length; primaries === 1 && secondaries === 2 ? 1 : 0 } catch (error) { 0 }')" = "1" ]; do
    echo "waiting for replica set $name"
    sleep 2
  done
}

ensure_replset() {
  name="$1"
  host="$2"
  port="$3"
  config="$4"

  if [ "$(mongo_result "$host" "$port" 'try { rs.status().ok } catch (error) { 0 }')" != "1" ]; then
    echo "initializing replica set $name"
    mongosh --quiet --host "$host" --port "$port" --eval "rs.initiate($config)"
  fi

  wait_for_replset_ready "$name" "$host" "$port"
}

ensure_shard_added() {
  shard_name="$1"
  replica_set="$2"
  members="$3"

  if [ "$(mongo_result "$MONGODB_HOST" "$MONGODB_PORT" "db.getSiblingDB(\"config\").shards.findOne({ _id: \"$shard_name\" }) ? 1 : 0")" != "1" ]; then
    echo "adding shard $shard_name"
    mongosh --quiet --host "$MONGODB_HOST" --port "$MONGODB_PORT" --eval "db.adminCommand({ addShard: \"$replica_set/$members\", name: \"$shard_name\" })"
  fi
}

ensure_database_sharding() {
  if [ "$(mongo_result "$MONGODB_HOST" "$MONGODB_PORT" "const database = db.getSiblingDB(\"config\").databases.findOne({ _id: \"$MONGODB_DATABASE\" }); database && database.partitioned ? 1 : 0")" != "1" ]; then
    echo "enabling sharding for $MONGODB_DATABASE"
    mongosh --quiet --host "$MONGODB_HOST" --port "$MONGODB_PORT" --eval "db.adminCommand({ enableSharding: \"$MONGODB_DATABASE\" })"
  fi
}

ensure_events_collection_sharded() {
  namespace="$MONGODB_DATABASE.events"

  if [ "$(mongo_result "$MONGODB_HOST" "$MONGODB_PORT" "const collection = db.getSiblingDB(\"config\").collections.findOne({ _id: \"$namespace\" }); collection && collection.key ? 1 : 0")" != "1" ]; then
    echo "sharding collection $namespace"
    mongosh --quiet --host "$MONGODB_HOST" --port "$MONGODB_PORT" --eval "db.adminCommand({ shardCollection: \"$namespace\", key: { created_by: \"hashed\" } })"
  fi
}

wait_for_mongo "config server 1" "config1" "$CONFIG1_PORT"
wait_for_mongo "config server 2" "config2" "$CONFIG2_PORT"
wait_for_mongo "config server 3" "config3" "$CONFIG3_PORT"

config_replset_config="{
  _id: \"$CONFIGRS_NAME\",
  configsvr: true,
  members: [
    { _id: 0, host: \"config1:$CONFIG1_PORT\" },
    { _id: 1, host: \"config2:$CONFIG2_PORT\" },
    { _id: 2, host: \"config3:$CONFIG3_PORT\" }
  ]
}"
ensure_replset \
  "$CONFIGRS_NAME" \
  "config1" \
  "$CONFIG1_PORT" \
  "$config_replset_config"

wait_for_mongo "shard 1 node 1" "shard1a" "$SHARD1_A_PORT"
wait_for_mongo "shard 1 node 2" "shard1b" "$SHARD1_B_PORT"
wait_for_mongo "shard 1 node 3" "shard1c" "$SHARD1_C_PORT"

shard_1_replset_config="{
  _id: \"$SHARD1_RS_NAME\",
  members: [
    { _id: 0, host: \"shard1a:$SHARD1_A_PORT\" },
    { _id: 1, host: \"shard1b:$SHARD1_B_PORT\" },
    { _id: 2, host: \"shard1c:$SHARD1_C_PORT\" }
  ]
}"
ensure_replset \
  "$SHARD1_RS_NAME" \
  "shard1a" \
  "$SHARD1_A_PORT" \
  "$shard_1_replset_config"

wait_for_mongo "shard 2 node 1" "shard2a" "$SHARD2_A_PORT"
wait_for_mongo "shard 2 node 2" "shard2b" "$SHARD2_B_PORT"
wait_for_mongo "shard 2 node 3" "shard2c" "$SHARD2_C_PORT"

shard_2_replset_config="{
  _id: \"$SHARD2_RS_NAME\",
  members: [
    { _id: 0, host: \"shard2a:$SHARD2_A_PORT\" },
    { _id: 1, host: \"shard2b:$SHARD2_B_PORT\" },
    { _id: 2, host: \"shard2c:$SHARD2_C_PORT\" }
  ]
}"
ensure_replset \
  "$SHARD2_RS_NAME" \
  "shard2a" \
  "$SHARD2_A_PORT" \
  "$shard_2_replset_config"

wait_for_mongo "mongos router" "$MONGODB_HOST" "$MONGODB_PORT"

ensure_shard_added \
  "$SHARD1_RS_NAME" \
  "$SHARD1_RS_NAME" \
  "shard1a:$SHARD1_A_PORT,shard1b:$SHARD1_B_PORT,shard1c:$SHARD1_C_PORT"

ensure_shard_added \
  "$SHARD2_RS_NAME" \
  "$SHARD2_RS_NAME" \
  "shard2a:$SHARD2_A_PORT,shard2b:$SHARD2_B_PORT,shard2c:$SHARD2_C_PORT"

ensure_database_sharding
ensure_events_collection_sharded

echo "mongodb cluster is ready"
