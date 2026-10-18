-- Initial Database Schema for City Planner Geo
-- T0.4: Projeto Supabase

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Table: projects
-- Stores information about city planning projects
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table: analysis_areas
-- Stores the geographical areas being analyzed (with PostGIS geometry)
CREATE TABLE analysis_areas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    -- Geometry column for storing the analysis area polygon/multipolygon
    geom GEOMETRY(MULTIPOLYGON, 4326), -- WGS 84
    -- Optional: simplified geometry for faster operations
    geom_simplified GEOMETRY(MULTIPOLYGON, 4326),
    area_m2 DOUBLE PRECISION CHECK (area_m2 >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create spatial index for geometry column
CREATE INDEX idx_analysis_areas_geom ON analysis_areas USING GIST (geom);
CREATE INDEX idx_analysis_areas_geom_simplified ON analysis_areas USING GIST (geom_simplified);

-- Table: reports
-- Stores generated reports (PDF, etc.)
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_area_id UUID REFERENCES analysis_areas(id) ON DELETE CASCADE NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    -- Reference to file in Supabase Storage
    storage_bucket VARCHAR(100) DEFAULT 'reports',
    storage_path TEXT,
    file_size_bytes INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table: datasets_cache
-- Cache for external datasets to avoid repeated API calls
CREATE TABLE datasets_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_source VARCHAR(100) NOT NULL, -- e.g., 'GBIF', 'INTERGEOPT', 'TIMO_DS', 'THE_WELL'
    dataset_type VARCHAR(100) NOT NULL, -- e.g., 'species', 'forest_cover', 'soil_type'
    geographic_bounds GEOMETRY(POLYGON, 4326), -- Area this cache entry covers
    cached_data JSONB, -- The actual cached data
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for efficient cache lookup by geographic area and expiration
CREATE INDEX idx_datasets_cache_bounds_expires ON datasets_cache USING GIST (geographic_bounds)
    WHERE expires_at > NOW();

-- Table: materials
-- Catalog of construction materials with properties
CREATE TABLE materials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL, -- e.g., 'concrete', 'steel', 'wood', 'insulation'
    properties JSONB, -- Material-specific properties (density, strength, etc.)
    unit_cost NUMERIC(10, 2), -- Cost per unit
    unit VARCHAR(50), -- e.g., 'm³', 'kg', 'm²'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table: model_checkpoints
-- Stores information about ML model checkpoints
CREATE TABLE model_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50),
    description TEXT,
    model_type VARCHAR(100), -- e.g., 'species_prediction', 'forest_growth', 'structural_load'
    region_covered GEOMETRY(POLYGON, 4326), -- Geographic region this checkpoint is valid for
    -- Reference to file in Supabase Storage
    storage_bucket VARCHAR(100) DEFAULT 'model-checkpoints',
    storage_path TEXT,
    file_size_bytes INTEGER,
    performance_metrics JSONB, -- Metrics like accuracy, precision, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security (RLS) on all tables
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_areas ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE datasets_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE materials ENABLE ROW LEVEL SECURITY;
ALTER TABLE model_checkpoints ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
-- Users can only access their own data
CREATE POLICY project_rls ON projects
    FOR ALL
    USING (auth.uid() = user_id);

CREATE POLICY analysis_area_rls ON analysis_areas
    FOR ALL
    USING (EXISTS (
        SELECT 1 FROM projects WHERE projects.id = analysis_areas.project_id AND projects.user_id = auth.uid()
    ));

CREATE POLICY report_rls ON reports
    FOR ALL
    USING (EXISTS (
        SELECT 1 FROM analysis_areas
        JOIN projects ON analysis_areas.project_id = projects.id
        WHERE analysis_areas.id = reports.analysis_area_id AND projects.user_id = auth.uid()
    ));

CREATE POLICY material_rls ON materials
    FOR ALL
    USING (true); -- Materials are publicly readable

CREATE POLICY model_checkpoint_rls ON model_checkpoints
    FOR ALL
    USING (true); -- Model checkpoints are publicly readable

CREATE POLICY datasets_cache_rls ON datasets_cache
    FOR ALL
    USING (true); -- Cache is publicly readable

-- Grant necessary permissions to authenticated users and service role
-- These would typically be configured in the Supabase dashboard
-- but are included here for completeness

-- Note: The auth.users table is managed by Supabase Auth
-- We reference it via foreign keys but don't manage it directly