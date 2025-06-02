-- Script d'initialisation de la base de données MAR
-- Ce script sera exécuté automatiquement lors du premier démarrage de PostgreSQL

-- Création de la base de données si elle n'existe pas
SELECT 'CREATE DATABASE mar_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mar_db')\gexec

-- Connexion à la base de données
\c mar_db;

-- Création du schéma de base
CREATE SCHEMA IF NOT EXISTS mar;

-- Extension pour UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table des documents
CREATE TABLE IF NOT EXISTS mar.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    content TEXT,
    file_path VARCHAR(500),
    file_type VARCHAR(50),
    file_size BIGINT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des embeddings
CREATE TABLE IF NOT EXISTS mar.embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES mar.documents(id) ON DELETE CASCADE,
    chunk_index INTEGER,
    content TEXT NOT NULL,
    embedding VECTOR(768),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des agents
CREATE TABLE IF NOT EXISTS mar.agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    config JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des tâches
CREATE TABLE IF NOT EXISTS mar.tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES mar.agents(id),
    type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour optimiser les performances
CREATE INDEX IF NOT EXISTS idx_documents_processed ON mar.documents(processed);
CREATE INDEX IF NOT EXISTS idx_documents_file_type ON mar.documents(file_type);
CREATE INDEX IF NOT EXISTS idx_embeddings_document_id ON mar.embeddings(document_id);
CREATE INDEX IF NOT EXISTS idx_tasks_agent_id ON mar.tasks(agent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON mar.tasks(status);

-- Insertion de données de test
INSERT INTO mar.agents (name, type, config) VALUES 
('Ingestion Agent', 'ingestion', '{"max_file_size": 10485760}'),
('Vectorization Agent', 'vectorization', '{"model": "sentence-transformers"}'),
('Retrieval Agent', 'retrieval', '{"top_k": 10}'),
('Synthesis Agent', 'synthesis', '{"model": "llama"}')
ON CONFLICT DO NOTHING;

GRANT ALL PRIVILEGES ON SCHEMA mar TO mar_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA mar TO mar_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA mar TO mar_user;
