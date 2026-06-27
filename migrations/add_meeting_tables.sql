-- Create meetings table
CREATE TABLE IF NOT EXISTS meetings (
    id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    participants TEXT,
    transcript TEXT,
    summary TEXT,
    decisions_count INT DEFAULT 0,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create decision votes table
CREATE TABLE IF NOT EXISTS decision_votes (
    id SERIAL PRIMARY KEY,
    decision_id VARCHAR(50) NOT NULL,
    vote VARCHAR(50),
    voted_by VARCHAR(255),
    voted_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (decision_id) REFERENCES decisions(id) ON DELETE CASCADE
);

-- Create meeting transcripts table
CREATE TABLE IF NOT EXISTS meeting_transcripts (
    id SERIAL PRIMARY KEY,
    meeting_id VARCHAR(50) NOT NULL,
    speaker VARCHAR(255),
    text TEXT,
    timestamp TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_meetings_date ON meetings(started_at);
CREATE INDEX IF NOT EXISTS idx_decision_votes_decision ON decision_votes(decision_id);
CREATE INDEX IF NOT EXISTS idx_decision_votes_user ON decision_votes(voted_by);
CREATE INDEX IF NOT EXISTS idx_transcripts_meeting ON meeting_transcripts(meeting_id);