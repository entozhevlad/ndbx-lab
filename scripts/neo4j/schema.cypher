// Схема графа Neo4j для рекомендаций мероприятий

CREATE CONSTRAINT user_id_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.id IS UNIQUE;

CREATE CONSTRAINT event_id_unique IF NOT EXISTS
FOR (e:Event) REQUIRE e.id IS UNIQUE;

CREATE INDEX event_title_idx IF NOT EXISTS
FOR (e:Event) ON (e.title);
