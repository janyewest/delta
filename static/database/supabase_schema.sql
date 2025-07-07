-- Create schema
create schema consulting;

-- Schema policies
GRANT USAGE ON SCHEMA consulting TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA consulting TO anon, authenticated, service_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA consulting
  GRANT ALL ON TABLES TO anon, authenticated, service_role;

-- Table to store past client projects
create table consulting.clients (
  id uuid not null default gen_random_uuid (),
  name text not null,
  industry text not null,
  description text not null,
  created_at timestamp with time zone not null,
  constraint clients_pkey primary key (id)
);

-- Table to simulate a history of statements of work (SOWs)
create table consulting.sows (
  id uuid not null default gen_random_uuid (),
  client_id uuid not null,
  sow_title text not null,
  content text not null,
  created_at timestamp with time zone not null,
  constraint sows_pkey primary key (id),
  constraint sows_client_id_fkey foreign KEY (client_id) references consulting.clients (id) on update CASCADE on delete CASCADE
);

-- Table to store summaries of solutions for clients
create table consulting.solutions (
  id uuid not null default gen_random_uuid (),
  sow_id uuid not null,
  summary text not null,
  technologies text[] not null,
  team_size smallint not null,
  duration_weeks smallint not null,
  created_at timestamp with time zone not null,
  constraint solutions_pkey primary key (id),
  constraint solutions_sow_id_fkey foreign KEY (sow_id) references consulting.sows (id) on update CASCADE on delete CASCADE
);

create table consulting.embeddings (
  id uuid not null default gen_random_uuid (),
  sow_id uuid not null,
  content text null,
  embedding text null,
  constraint embeddings_pkey primary key (id),
  constraint embeddings_sow_id_key unique (sow_id),
  constraint embeddings_sow_id_fkey foreign KEY (sow_id) references consulting.sows (id) on delete CASCADE
);

create table consulting.saved_suggestions (
  id uuid not null default gen_random_uuid (),
  prompt text not null,
  suggestions text[] null,
  created_at timestamp without time zone null default now(),
  constraint saved_suggestions_pkey primary key (id)
);
