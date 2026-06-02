CREATE TABLE IF NOT EXISTS chat_feedback (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL,
    source      VARCHAR(20) NOT NULL,   -- 'graph' | 'llm'
    verdict     VARCHAR(20),            -- 'correct' | 'wrong' | 'partial'
    correction  TEXT,                   -- user's correction if wrong
    features_referenced TEXT[],        -- feature names mentioned in answer
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_feedback_verdict   ON chat_feedback(verdict);
CREATE INDEX IF NOT EXISTS idx_chat_feedback_source    ON chat_feedback(source);
CREATE INDEX IF NOT EXISTS idx_chat_feedback_created   ON chat_feedback(created_at DESC);
