-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create initial schema
CREATE SCHEMA IF NOT EXISTS research_mind;

-- Set default search path
ALTER DATABASE researchmind SET search_path TO research_mind, public;
